from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models


class ConfiguracaoNotificacao(models.Model):
    """
    Configuração única (singleton) de pra onde mandar os alertas
    automáticos. Sempre acessada via `get_config()`.
    """
    email_destino = models.EmailField("E-mail pra receber alertas", blank=True)
    ativar_email = models.BooleanField("Ativar alertas por e-mail", default=True)

    whatsapp_numero = models.CharField(
        "WhatsApp pra receber alertas", max_length=20, blank=True,
        help_text="Formato internacional, ex: +5511999999999. Requer conta Twilio configurada (veja o README).",
    )
    ativar_whatsapp = models.BooleanField("Ativar alertas por WhatsApp", default=False)

    limite_diferenca_caixa = models.DecimalField(
        "Alertar se a diferença no fechamento de caixa passar de (R$)",
        max_digits=10, decimal_places=2, default=Decimal("20.00"),
        validators=[MinValueValidator(0)],
    )
    dias_aviso_vencimento = models.PositiveIntegerField(
        "Avisar sobre contas vencendo em quantos dias", default=2,
    )

    class Meta:
        verbose_name = "Configuração de notificações"
        verbose_name_plural = "Configuração de notificações"

    def __str__(self):
        return "Configuração de notificações"


def get_config():
    config, _ = ConfiguracaoNotificacao.objects.get_or_create(pk=1)
    return config


class ConfiguracaoPush(models.Model):
    """
    Par de chaves VAPID (usado pra autenticar as notificações push do
    navegador) — gerado sozinho na primeira vez que for preciso,
    sem precisar configurar nada manualmente.
    """
    chave_publica = models.TextField(blank=True)
    chave_privada = models.TextField(blank=True)

    class Meta:
        verbose_name = "Configuração de notificações push"
        verbose_name_plural = "Configuração de notificações push"

    def __str__(self):
        return "Configuração de notificações push"


class InscricaoPush(models.Model):
    """Uma inscrição de notificação push de um navegador/dispositivo específico."""
    usuario = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="inscricoes_push"
    )
    endpoint = models.TextField(unique=True)
    p256dh_key = models.CharField(max_length=255)
    auth_key = models.CharField(max_length=255)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Inscrição push"
        verbose_name_plural = "Inscrições push"

    def __str__(self):
        return f"{self.usuario.username} — {self.endpoint[:40]}..."


def get_config_push():
    config, _ = ConfiguracaoPush.objects.get_or_create(pk=1)
    if not config.chave_publica or not config.chave_privada:
        import base64
        from py_vapid import Vapid

        vapid = Vapid()
        vapid.generate_keys()

        pub_numbers = vapid.public_key.public_numbers()
        chave_publica_raw = b"\x04" + pub_numbers.x.to_bytes(32, "big") + pub_numbers.y.to_bytes(32, "big")
        config.chave_publica = base64.urlsafe_b64encode(chave_publica_raw).decode().rstrip("=")

        priv_numbers = vapid.private_key.private_numbers()
        chave_privada_raw = priv_numbers.private_value.to_bytes(32, "big")
        config.chave_privada = base64.urlsafe_b64encode(chave_privada_raw).decode().rstrip("=")

        config.save()
    return config
