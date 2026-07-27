from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.encrypted_fields import CampoCriptografado


class Fornecedor(models.Model):
    AVALIACAO_CHOICES = [(i, f"{i} estrela{'s' if i > 1 else ''}") for i in range(1, 6)]

    nome = models.CharField(max_length=150)
    documento = CampoCriptografado("CNPJ/CPF", max_length=500, blank=True)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    avaliacao = models.PositiveSmallIntegerField(
        "Avaliação (1-5 estrelas)", choices=AVALIACAO_CHOICES, null=True, blank=True,
        help_text="Sua nota manual sobre esse fornecedor — qualidade, atendimento, confiabilidade.",
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class OrdemCompra(models.Model):
    """
    Registra a intenção de compra de estoque junto a um fornecedor.
    Quando marcada como 'recebida', o sistema automaticamente:
    - dá entrada no estoque de cada item
    - cria a conta a pagar correspondente ao fornecedor
    """

    STATUS_CHOICES = [
        ("pendente_aprovacao", "Aguardando aprovação"),
        ("aberta", "Aberta"),
        ("parcial", "Recebida parcialmente"),
        ("recebida", "Recebida"),
        ("cancelada", "Cancelada"),
    ]

    fornecedor = models.ForeignKey(
        Fornecedor, on_delete=models.PROTECT, related_name="ordens_compra"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")
    data_prevista = models.DateField(null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)
    recebida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Ordem de compra"
        verbose_name_plural = "Ordens de compra"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"OC #{self.pk} — {self.fornecedor.nome}"

    @property
    def valor_total(self):
        from django.db.models import F, Sum
        total = self.itens.aggregate(t=Sum(F("quantidade") * F("preco_unitario")))["t"]
        return total or 0

    @property
    def total(self):
        return sum(
            (item.quantidade * item.preco_unitario for item in self.itens.all()),
            Decimal("0"),
        )

    @property
    def tem_backorder(self):
        return any(item.pendente > 0 for item in self.itens.all())

    @property
    def dias_ate_recebimento(self):
        if not self.recebida_em:
            return None
        return (self.recebida_em.date() - self.criada_em.date()).days

    @property
    def atraso_dias(self):
        if not self.recebida_em or not self.data_prevista:
            return None
        return (self.recebida_em.date() - self.data_prevista).days


class ItemOrdemCompra(models.Model):
    ordem = models.ForeignKey(OrdemCompra, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    quantidade_recebida = models.PositiveIntegerField(default=0)
    preco_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )

    class Meta:
        verbose_name = "Item da ordem de compra"
        verbose_name_plural = "Itens da ordem de compra"

    def __str__(self):
        return f"{self.quantidade}x {self.produto.sku}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    @property
    def pendente(self):
        """Quantidade que ainda falta chegar (backorder)."""
        return max(self.quantidade - self.quantidade_recebida, 0)

    @property
    def diferenca(self):
        """Positivo = recebeu a mais do que pediu. Negativo = ainda falta (backorder)."""
        return self.quantidade_recebida - self.quantidade


class Cotacao(models.Model):
    """
    Pede preço a vários fornecedores pros mesmos produtos antes de
    decidir com quem comprar. Ao finalizar, gera uma (ou mais) Ordem
    de compra a partir das propostas escolhidas.
    """
    STATUS_CHOICES = [("aberta", "Aberta"), ("finalizada", "Finalizada")]

    observacoes = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="aberta")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cotação"
        verbose_name_plural = "Cotações"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Cotação #{self.pk} ({self.get_status_display()})"


class ItemCotacao(models.Model):
    cotacao = models.ForeignKey(Cotacao, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Item da cotação"
        verbose_name_plural = "Itens da cotação"
        unique_together = ("cotacao", "produto")

    def __str__(self):
        return f"{self.quantidade}x {self.produto.sku}"

    @property
    def melhor_proposta(self):
        return self.propostas.order_by("preco_unitario").first()


class PropostaCotacao(models.Model):
    """O preço que UM fornecedor ofereceu pra UM item da cotação."""
    item_cotacao = models.ForeignKey(ItemCotacao, on_delete=models.CASCADE, related_name="propostas")
    fornecedor = models.ForeignKey(Fornecedor, on_delete=models.CASCADE, related_name="propostas_cotacao")
    preco_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    prazo_dias = models.PositiveIntegerField("Prazo de entrega (dias)", null=True, blank=True)
    observacoes = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Proposta de fornecedor"
        verbose_name_plural = "Propostas de fornecedores"
        unique_together = ("item_cotacao", "fornecedor")

    def __str__(self):
        return f"{self.fornecedor.nome} — R$ {self.preco_unitario}"
