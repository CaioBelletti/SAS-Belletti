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

from django.utils import timezone

from .models import TentativaLogin

LIMITE_TENTATIVAS = 5
JANELA_MINUTOS = 15
BLOQUEIO_MINUTOS = 15


def esta_bloqueado(username):
    desde = timezone.now() - timedelta(minutes=JANELA_MINUTOS)
    falhas = TentativaLogin.objects.filter(
        username__iexact=username, sucesso=False, criado_em__gte=desde
    ).count()
    return falhas >= LIMITE_TENTATIVAS


def minutos_restantes_bloqueio(username):
    desde = timezone.now() - timedelta(minutes=JANELA_MINUTOS)
    ultima_falha = (
        TentativaLogin.objects.filter(username__iexact=username, sucesso=False, criado_em__gte=desde)
        .order_by("-criado_em").first()
    )
    if not ultima_falha:
        return 0
    minutos_passados = (timezone.now() - ultima_falha.criado_em).total_seconds() / 60
    return max(int(BLOQUEIO_MINUTOS - minutos_passados) + 1, 0)


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
    return pyotp.TOTP(secret).verify(str(codigo).strip(), valid_window=1)
