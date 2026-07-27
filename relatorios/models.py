from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PreferenciaDashboard(models.Model):
    """
    Guarda a ordem e a visibilidade dos widgets do dashboard escolhidas
    por cada usuário (arrastar-e-soltar). Se o usuário nunca mexeu em
    nada, usamos a ordem padrão (ver WIDGETS_PADRAO em views.py).
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferencia_dashboard"
    )
    ordem_widgets = models.JSONField(default=list, blank=True)
    widgets_ocultos = models.JSONField(default=list, blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Preferência de dashboard"
        verbose_name_plural = "Preferências de dashboard"

    def __str__(self):
        return f"Preferência de dashboard de {self.usuario}"


class ConfiguracaoEstoque(models.Model):
    """Configuração única (singleton) do alerta de produtos parados."""
    dias_produto_parado = models.PositiveIntegerField(
        "Considerar 'parado' sem vender há quantos dias", default=60,
    )
    reposicao_automatica_ativa = models.BooleanField(
        "Gerar ordem de compra sozinho quando o estoque bater no mínimo", default=False,
        help_text="Só funciona pra produtos que já têm um fornecedor padrão definido na ficha.",
    )
    reposicao_multiplicador_minimo = models.PositiveIntegerField(
        "Quantidade sugerida = estoque mínimo × este número", default=3,
        help_text="Usado quando o produto não tem 'estoque máximo' definido.",
    )

    class Meta:
        verbose_name = "Configuração de estoque"
        verbose_name_plural = "Configuração de estoque"

    def __str__(self):
        return "Configuração de estoque"


def get_config_estoque():
    config, _ = ConfiguracaoEstoque.objects.get_or_create(pk=1)
    return config


class MetaMensal(models.Model):
    """Meta de faturamento definida pra um mês específico."""
    mes = models.DateField(
        "Mês (use o dia 1)", unique=True,
        help_text="Sempre o primeiro dia do mês, ex: 01/08/2026 pra meta de agosto.",
    )
    valor = models.DecimalField(
        "Meta de faturamento (R$)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Meta mensal"
        verbose_name_plural = "Metas mensais"
        ordering = ["-mes"]

    def __str__(self):
        return f"{self.mes.strftime('%m/%Y')} — R$ {self.valor}"


class ConfiguracaoRelatorioAutomatico(models.Model):
    FREQUENCIA_CHOICES = [
        ("diario", "Diário (todo dia)"),
        ("semanal", "Semanal (toda segunda-feira)"),
        ("mensal", "Mensal (todo dia 1º)"),
        ("anual", "Anual (todo dia 1º de janeiro)"),
    ]

    ativo = models.BooleanField("Enviar resumo automático por e-mail", default=False)
    frequencia = models.CharField(max_length=10, choices=FREQUENCIA_CHOICES, default="semanal")
    destinatario = models.EmailField("E-mail de destino", blank=True)
    ultimo_envio = models.DateField(null=True, blank=True, editable=False)

    class Meta:
        verbose_name = "Configuração de relatório automático"
        verbose_name_plural = "Configuração de relatório automático"

    def __str__(self):
        return "Configuração de relatório automático"


def get_config_relatorio_automatico():
    config, _ = ConfiguracaoRelatorioAutomatico.objects.get_or_create(pk=1)
    return config
