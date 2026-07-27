"""
Envio de alertas por e-mail (built-in do Django, sempre disponível) e
WhatsApp (via API do Twilio — opcional e pago, só funciona se as
variáveis de ambiente TWILIO_* estiverem configuradas).

Notificação nunca deve derrubar o fluxo principal do sistema — todas
as funções aqui engolem erro silenciosamente (fail_silently).
"""
import os

from django.core.mail import send_mail

from .models import get_config


def enviar_email(assunto, corpo):
    config = get_config()
    if not config.ativar_email or not config.email_destino:
        return
    send_mail(
        subject=f"[Belletti Cards Universe] {assunto}",
        message=corpo,
        from_email=None,  # usa DEFAULT_FROM_EMAIL
        recipient_list=[config.email_destino],
        fail_silently=True,
    )


def enviar_whatsapp(mensagem):
    config = get_config()
    if not config.ativar_whatsapp or not config.whatsapp_numero:
        return

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    numero_de = os.environ.get("TWILIO_WHATSAPP_FROM")  # ex: whatsapp:+14155238886
    if not (sid and token and numero_de):
        return

    try:
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        requests.post(
            url,
            data={"From": numero_de, "To": f"whatsapp:{config.whatsapp_numero}", "Body": mensagem},
            auth=(sid, token),
            timeout=10,
        )
    except Exception:
        pass


def notificar(assunto, mensagem):
    enviar_email(assunto, mensagem)
    enviar_whatsapp(f"{assunto}\n\n{mensagem}")


def enviar_email_para(destinatario, assunto, corpo):
    """Como enviar_email, mas pra um destinatário qualquer (ex: cliente), não só o e-mail de alerta configurado."""
    if not destinatario:
        return
    send_mail(
        subject=f"[Belletti Cards Universe] {assunto}",
        message=corpo,
        from_email=None,
        recipient_list=[destinatario],
        fail_silently=True,
    )


def enviar_whatsapp_para(numero, mensagem):
    """Como enviar_whatsapp, mas pra um número qualquer (ex: cliente), não só o número de alerta configurado."""
    if not numero:
        return

    sid = os.environ.get("TWILIO_ACCOUNT_SID")
    token = os.environ.get("TWILIO_AUTH_TOKEN")
    numero_de = os.environ.get("TWILIO_WHATSAPP_FROM")
    if not (sid and token and numero_de):
        return

    try:
        import requests
        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        requests.post(
            url,
            data={"From": numero_de, "To": f"whatsapp:{numero}", "Body": mensagem},
            auth=(sid, token),
            timeout=10,
        )
    except Exception:
        pass


def enviar_push_para_usuario(usuario, titulo, corpo, url_destino="/relatorios/"):
    """Manda notificação push pra todos os dispositivos inscritos desse usuário."""
    import json

    from pywebpush import WebPushException, webpush

    from .models import InscricaoPush, get_config_push

    config = get_config_push()
    inscricoes = InscricaoPush.objects.filter(usuario=usuario)
    enviadas = 0

    for inscricao in inscricoes:
        subscription_info = {
            "endpoint": inscricao.endpoint,
            "keys": {"p256dh": inscricao.p256dh_key, "auth": inscricao.auth_key},
        }
        try:
            webpush(
                subscription_info=subscription_info,
                data=json.dumps({"titulo": titulo, "corpo": corpo, "url": url_destino}),
                vapid_private_key=config.chave_privada,
                vapid_claims={"sub": "mailto:contato@belletticards.com.br"},
            )
            enviadas += 1
        except WebPushException as exc:
            # inscrição expirada/inválida (ex: usuário desinstalou) — remove
            if exc.response is not None and exc.response.status_code in (404, 410):
                inscricao.delete()
    return enviadas


def enviar_push_para_staff(titulo, corpo, url_destino="/relatorios/"):
    """Manda notificação push pra todo mundo que é staff e tem alguma inscrição ativa."""
    from django.contrib.auth import get_user_model

    from .models import InscricaoPush

    usuarios_com_inscricao = get_user_model().objects.filter(
        is_staff=True, inscricoes_push__isnull=False
    ).distinct()
    total = 0
    for usuario in usuarios_com_inscricao:
        total += enviar_push_para_usuario(usuario, titulo, corpo, url_destino)
    return total
