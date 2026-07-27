from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

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
            request.session["pre_2fa_user_id"] = user.id
            request.session["pre_2fa_next"] = proximo
            return redirect("seguranca:verificar_2fa")

        login(request, user)
        registrar_sessao_ativa(request, user)
        return redirect(proximo)

    return render(request, "seguranca/login.html", {"next": proximo})


def verificar_2fa_view(request):
    user_id = request.session.get("pre_2fa_user_id")
    if not user_id:
        return redirect("login")

    user = User.objects.filter(pk=user_id).first()
    if not user:
        request.session.pop("pre_2fa_user_id", None)
        return redirect("login")

    if request.method == "POST":
        codigo = request.POST.get("codigo", "")
        chave_bloqueio = f"2fa:{user.username}"

        if esta_bloqueado(chave_bloqueio):
            minutos = minutos_restantes_bloqueio(chave_bloqueio)
            messages.error(request, f"Muitas tentativas erradas. Tente de novo em {minutos} minuto(s).")
            return render(request, "seguranca/verificar_2fa.html")

        dois_fatores = DoisFatores.objects.get(usuario=user, ativado=True)
        if verificar_codigo_totp(dois_fatores.secret, codigo):
            registrar_tentativa(chave_bloqueio, sucesso=True)
            proximo = request.session.pop("pre_2fa_next", "/")
            request.session.pop("pre_2fa_user_id", None)
            login(request, user)
            registrar_sessao_ativa(request, user)
            return redirect(proximo)

        registrar_tentativa(chave_bloqueio, sucesso=False)
        messages.error(request, "Código inválido.")

    return render(request, "seguranca/verificar_2fa.html")


@login_required
def configurar_2fa_view(request):
    dois_fatores = DoisFatores.objects.filter(usuario=request.user).first()

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "desativar":
            if dois_fatores:
                dois_fatores.ativado = False
                dois_fatores.save(update_fields=["ativado"])
            messages.success(request, "Autenticação em duas etapas desativada.")
            return redirect("seguranca:configurar_2fa")

        if acao == "confirmar":
            secret_pendente = request.session.get("2fa_secret_pendente")
            codigo = request.POST.get("codigo", "")
            if secret_pendente and verificar_codigo_totp(secret_pendente, codigo):
                DoisFatores.objects.update_or_create(
                    usuario=request.user,
                    defaults={"secret": secret_pendente, "ativado": True},
                )
                request.session.pop("2fa_secret_pendente", None)
                messages.success(request, "Autenticação em duas etapas ativada com sucesso!")
                return redirect("seguranca:configurar_2fa")
            messages.error(request, "Código inválido. Tente escanear o QR code de novo.")

    qr_data_uri = None
    if not (dois_fatores and dois_fatores.ativado):
        secret = request.session.get("2fa_secret_pendente")
        if not secret:
            secret = gerar_secret()
            request.session["2fa_secret_pendente"] = secret
        qr_data_uri = gerar_qr_data_uri(request.user.username, secret)

    return render(request, "seguranca/configurar_2fa.html", {
        "ativado": bool(dois_fatores and dois_fatores.ativado),
        "qr_data_uri": qr_data_uri,
    })
