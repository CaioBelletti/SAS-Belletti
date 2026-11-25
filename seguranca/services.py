"""
Duas camadas de segurança de login:

1. Bloqueio por tentativas: depois de LIMITE_TENTATIVAS falhas (login
   ou código 2FA errado) dentro de JANELA_MINUTOS, o usuário fica
   impedido de tentar de novo por BLOQUEIO_MINUTOS.
2. TOTP (autenticação em duas etapas): código de 6 dígitos gerado por
   um app autenticador (Google Authenticator, Authy, etc), válido por
   ~30 segundos, sem depender de SMS ou serviço pago.
"""
from datetime import timedelta
from math import ceil
import re

from django.utils import timezone

from .models import TentativaLogin

LIMITE_TENTATIVAS = 5
JANELA_MINUTOS = 15
BLOQUEIO_MINUTOS = 15


def segundos_restantes_bloqueio(username):
    agora = timezone.now()
    desde = agora - timedelta(minutes=JANELA_MINUTOS + BLOQUEIO_MINUTOS)
    falhas = list(TentativaLogin.objects.filter(
        username__iexact=username, sucesso=False, criado_em__gte=desde
    ).order_by("-criado_em").values_list("criado_em", flat=True)[:LIMITE_TENTATIVAS])
    if len(falhas) < LIMITE_TENTATIVAS:
        return 0
    if falhas[0] - falhas[-1] > timedelta(minutes=JANELA_MINUTOS):
        return 0
    fim = falhas[0] + timedelta(minutes=BLOQUEIO_MINUTOS)
    return max(0, ceil((fim - agora).total_seconds()))


def esta_bloqueado(username):
    return segundos_restantes_bloqueio(username) > 0


def minutos_restantes_bloqueio(username):
    return ceil(segundos_restantes_bloqueio(username) / 60)


def registrar_tentativa(username, sucesso, ip=""):
    TentativaLogin.objects.create(username=username, sucesso=sucesso, ip=ip)
    if sucesso:
        # login bem-sucedido limpa o histórico de falhas — recomeça do zero
        TentativaLogin.objects.filter(username__iexact=username, sucesso=False).delete()


def get_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def registrar_sessao_ativa(request, usuario):
    """Chamar logo depois de login(request, usuario) — cria/atualiza o registro de sessão ativa."""
    from .models import SessaoAtiva

    if not request.session.session_key:
        request.session.save()

    SessaoAtiva.objects.update_or_create(
        session_key=request.session.session_key,
        defaults={
            "usuario": usuario,
            "ip": get_ip(request),
            "dispositivo": request.META.get("HTTP_USER_AGENT", "")[:255],
        },
    )


# --- TOTP (2FA) ------------------------------------------------------------

def gerar_secret():
    import pyotp
    return pyotp.random_base32()


def gerar_qr_data_uri(usuario_username, secret):
    """Devolve o QR code já como data URI, pra colocar direto num <img src=...>."""
    import base64
    import io

    import pyotp
    import qrcode

    uri = pyotp.TOTP(secret).provisioning_uri(
        name=usuario_username, issuer_name="Belletti Cards Universe"
    )
    img = qrcode.make(uri)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    b64 = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def verificar_codigo_totp(secret, codigo):
    import pyotp
    codigo = str(codigo).strip()
    if not re.fullmatch(r"[0-9]{6}", codigo):
        return False
    try:
        return pyotp.TOTP(secret).verify(codigo, valid_window=1)
    except (ValueError, TypeError):
        return False
