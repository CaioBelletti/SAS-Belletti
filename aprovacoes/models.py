from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class RegraAprovacao(models.Model):
    """
    Configura, pra cada tipo de operação, a partir de que valor ela
    passa a exigir aprovação, e por quais níveis (grupos) precisa
    passar em sequência antes de ser liberada.
    """
    TIPO_CHOICES = [
        ("compra", "Ordem de compra"),
        ("pagamento", "Conta a pagar"),
        ("desconto", "Desconto de venda no PDV"),
    ]

    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, unique=True)
    ativa = models.BooleanField("Exigir aprovação pra esse tipo", default=False)
    valor_limite = models.DecimalField(
        "A partir de que valor exige aprovação", max_digits=10, decimal_places=2, default=0,
        help_text="Pra desconto, esse valor é em R$ (desconto absoluto na venda), não percentual.",
    )

    class Meta:
        verbose_name = "Regra de aprovação"
        verbose_name_plural = "Regras de aprovação"

    def __str__(self):
        return f"{self.get_tipo_display()} — acima de R$ {self.valor_limite}"


class NivelAprovacao(models.Model):
    """Um degrau na cadeia de aprovação de uma regra — ex: nível 1 = Gerente, nível 2 = Financeiro."""
    regra = models.ForeignKey(RegraAprovacao, on_delete=models.CASCADE, related_name="niveis")
    ordem = models.PositiveSmallIntegerField()
    grupo_aprovador = models.ForeignKey(Group, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Nível de aprovação"
        verbose_name_plural = "Níveis de aprovação"
        ordering = ["regra", "ordem"]
        unique_together = ("regra", "ordem")

    def __str__(self):
        return f"{self.regra.get_tipo_display()} — nível {self.ordem} ({self.grupo_aprovador.name})"


class SolicitacaoAprovacao(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("aprovada", "Aprovada"),
        ("rejeitada", "Rejeitada"),
    ]

    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    objeto = GenericForeignKey("content_type", "object_id")

    tipo = models.CharField(max_length=15, choices=RegraAprovacao.TIPO_CHOICES)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    solicitado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="solicitacoes_feitas"
    )
    nivel_atual = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    criada_em = models.DateTimeField(auto_now_add=True)
    finalizada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Solicitação de aprovação"
        verbose_name_plural = "Solicitações de aprovação"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.descricao} ({self.get_status_display()})"

    @property
    def total_niveis(self):
        return RegraAprovacao.objects.get(tipo=self.tipo).niveis.count()

    def grupo_do_nivel_atual(self):
        nivel = NivelAprovacao.objects.filter(
            regra__tipo=self.tipo, ordem=self.nivel_atual
        ).select_related("grupo_aprovador").first()
        return nivel.grupo_aprovador if nivel else None


class RegistroDecisao(models.Model):
    solicitacao = models.ForeignKey(SolicitacaoAprovacao, on_delete=models.CASCADE, related_name="registros")
    nivel = models.PositiveSmallIntegerField()
    aprovador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    decisao = models.CharField(max_length=10, choices=[("aprovado", "Aprovado"), ("rejeitado", "Rejeitado")])
    comentario = models.TextField(blank=True)
    decidido_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Registro de decisão"
        verbose_name_plural = "Registros de decisão"
        ordering = ["decidido_em"]

    def __str__(self):
        return f"Nível {self.nivel} — {self.get_decisao_display()} por {self.aprovador}"
