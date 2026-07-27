from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    """
    Log de quem fez o quê no sistema — vendas fechadas, caixa aberto/
    fechado, devoluções processadas, ordens de compra recebidas, etc.
    Nunca editado manualmente, só criado via `registrar()`.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    acao = models.CharField(max_length=60)
    descricao = models.CharField(max_length=255)
    ip = models.CharField(max_length=45, blank=True)
    dispositivo = models.CharField(max_length=255, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de auditoria"
        verbose_name_plural = "Registros de auditoria"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.acao} — {self.usuario} ({self.criado_em:%d/%m %H:%M})"


def _extrair_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def registrar(usuario, acao, descricao, request=None):
    ip = ""
    dispositivo = ""
    if request is not None:
        ip = _extrair_ip(request)
        dispositivo = request.META.get("HTTP_USER_AGENT", "")[:255]
    return RegistroAuditoria.objects.create(
        usuario=usuario, acao=acao, descricao=descricao, ip=ip, dispositivo=dispositivo,
    )
