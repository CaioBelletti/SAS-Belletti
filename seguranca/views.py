from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from .recovery import consumir_codigo, consumir_totp, gerar_codigos

from .models import DoisFatores
from .services import (
    esta_bloqueado,
    gerar_qr_data_uri,
    gerar_secret,
    get_ip,
    minutos_restantes_bloqueio,
    registrar_sessao_ativa,
    registrar_tentativa,
    verificar_codigo_totp,
)

User = get_user_model()


@login_required
def sessoes_view(request):
    from django.contrib.sessions.models import Session

    from .models import SessaoAtiva

    if not request.user.is_staff:
        return redirect("relatorios:dashboard")

    if request.method == "POST" and request.POST.get("acao") == "encerrar":
        sessao = SessaoAtiva.objects.filter(pk=request.POST.get("sessao_id")).first()
        if sessao:
            Session.objects.filter(session_key=sessao.session_key).delete()
            sessao.delete()
            messages.success(request, "Sessão encerrada.")
        return redirect("seguranca:sessoes")

    sessoes = SessaoAtiva.objects.select_related("usuario").order_by("-ultima_atividade")
    return render(request, "seguranca/sessoes.html", {
        "sessoes": sessoes, "sessao_atual_key": request.session.session_key,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect("relatorios:dashboard")

    proximo = request.GET.get("next") or request.POST.get("next") or "/"

    if not url_has_allowed_host_and_scheme(proximo, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        proximo = "/"

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        if esta_bloqueado(username):
            minutos = minutos_restantes_bloqueio(username)
            messages.error(
                request,
                f"Muitas tentativas erradas. Tente de novo em {minutos} minuto(s).",
            )
            return render(request, "seguranca/login.html", {"next": proximo})

        user = authenticate(request, username=username, password=password)
        ip = get_ip(request)

        if user is None:
            registrar_tentativa(username, sucesso=False, ip=ip)
            messages.error(request, "Usuário ou senha incorretos.")
            return render(request, "seguranca/login.html", {"next": proximo})

        registrar_tentativa(username, sucesso=True, ip=ip)

        dois_fatores = DoisFatores.objects.filter(usuario=user, ativado=True).first()
        if dois_fatores:
            request.session.cycle_key()
            request.session["pre_2fa_started"] = timezone.now().timestamp()
            request.session["pre_2fa_backend"] = user.backend
            request.session["pre_2fa_user_id"] = user.id
            request.session["pre_2fa_next"] = proximo
            return redirect("seguranca:verificar_2fa")

        login(request, user)
        registrar_sessao_ativa(request, user)
        return redirect(proximo)

    return render(request, "seguranca/login.html", {"next": proximo})


@never_cache
def verificar_2fa_view(request):
    user_id = request.session.get("pre_2fa_user_id")
    started = request.session.get("pre_2fa_started", 0)
    user = User.objects.filter(pk=user_id, is_active=True).first() if user_id else None
    if not user or timezone.now().timestamp() - started > 600 or not DoisFatores.objects.filter(usuario=user, ativado=True).exists():
        for key in ("pre_2fa_user_id", "pre_2fa_next", "pre_2fa_started", "pre_2fa_backend"):
            request.session.pop(key, None)
        return redirect("login")

    chave = f"2fa:{user.pk}"
    if request.method == "POST":
        codigo = request.POST.get("codigo", "")
        with transaction.atomic():
            User.objects.select_for_update().get(pk=user.pk)
            if not esta_bloqueado(chave):
                valido = consumir_codigo(user, codigo) if request.POST.get("metodo") == "recuperacao" else consumir_totp(user, codigo)
                registrar_tentativa(chave, sucesso=valido, ip=get_ip(request))
                if valido:
                    proximo = request.session.pop("pre_2fa_next", "/")
                    backend = request.session.pop("pre_2fa_backend", None)
                    request.session.pop("pre_2fa_user_id", None)
                    request.session.pop("pre_2fa_started", None)
                    login(request, user, backend=backend)
                    registrar_sessao_ativa(request, user)
                    return redirect(proximo)
                messages.error(request, "Código inválido ou já utilizado.")
        if esta_bloqueado(chave):
            messages.error(request, f"Muitas tentativas. Aguarde {minutos_restantes_bloqueio(chave)} minuto(s).")
    from .services import segundos_restantes_bloqueio
    return render(request, "seguranca/verificar_2fa.html", {"bloqueio_segundos": segundos_restantes_bloqueio(chave)})


@login_required
@never_cache
def configurar_2fa_view(request):
    user = request.user
    chave = f"2fa-config:{user.pk}"
    codigos = []
    if request.method == "POST":
        with transaction.atomic():
            User.objects.select_for_update().get(pk=user.pk)
            config = DoisFatores.objects.filter(usuario=user).first()
            ativo = bool(config and config.ativado)
            acao = request.POST.get("acao")
            codigo = request.POST.get("codigo", "")
            if esta_bloqueado(chave):
                messages.error(request, "Muitas tentativas. Aguarde antes de tentar novamente.")
            elif not user.check_password(request.POST.get("password", "")):
                registrar_tentativa(chave, False, get_ip(request))
                messages.error(request, "Não foi possível confirmar sua identidade.")
            elif ativo and acao in ("desativar", "gerar_codigos"):
                if consumir_totp(user, codigo) or consumir_codigo(user, codigo):
                    registrar_tentativa(chave, True, get_ip(request))
                    if acao == "desativar":
                        config.ativado = False
                        config.save(update_fields=["ativado"])
                        config.codigos_recuperacao.all().delete()
                        request.session.pop("2fa_secret_pendente", None)
                        messages.success(request, "Autenticação em duas etapas desativada.")
                        return redirect("seguranca:configurar_2fa")
                    codigos = gerar_codigos(user)
                else:
                    registrar_tentativa(chave, False, get_ip(request))
                    messages.error(request, "Código inválido ou já utilizado.")
            elif not ativo and acao == "confirmar":
                secret = request.session.get("2fa_secret_pendente")
                if secret and verificar_codigo_totp(secret, codigo):
                    config, _ = DoisFatores.objects.update_or_create(usuario=user, defaults={"secret": secret, "ativado": True, "ultimo_totp": -1})
                    consumir_totp(user, codigo)
                    request.session.pop("2fa_secret_pendente", None)
                    registrar_tentativa(chave, True, get_ip(request))
                    codigos = gerar_codigos(user)
                    messages.success(request, "Autenticação em duas etapas ativada.")
                else:
                    registrar_tentativa(chave, False, get_ip(request))
                    messages.error(request, "Código inválido.")
    config = DoisFatores.objects.filter(usuario=user).first()
    ativo = bool(config and config.ativado)
    qr = None
    if not ativo:
        secret = request.session.get("2fa_secret_pendente")
        if not secret:
            secret = gerar_secret()
            request.session["2fa_secret_pendente"] = secret
        qr = gerar_qr_data_uri(user.username, secret)
    return render(request, "seguranca/configurar_2fa.html", {"ativado": ativo, "qr_data_uri": qr, "codigos": codigos})
