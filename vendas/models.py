from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.encrypted_fields import CampoCriptografado


class PerfilVendedor(models.Model):
    """Percentual de comissão de cada usuário que vende no PDV."""
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="perfil_vendedor"
    )
    percentual_comissao = models.DecimalField(
        "Comissão (%)", max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    class Meta:
        verbose_name = "Perfil de vendedor"
        verbose_name_plural = "Perfis de vendedor"

    def __str__(self):
        return f"{self.usuario} — {self.percentual_comissao}%"


class ConfiguracaoFidelidade(models.Model):
    """Configuração única (singleton) do programa de pontos."""
    ativo = models.BooleanField("Programa de fidelidade ativo", default=True)
    valor_por_ponto = models.DecimalField(
        "Cliente ganha 1 ponto a cada R$ gastos", max_digits=10, decimal_places=2,
        default=Decimal("10.00"), validators=[MinValueValidator(0.01)],
    )
    valor_resgate_ponto = models.DecimalField(
        "Cada ponto vale quanto de desconto (R$)", max_digits=10, decimal_places=2,
        default=Decimal("0.10"), validators=[MinValueValidator(0)],
    )
    percentual_cashback = models.DecimalField(
        "Cashback (% do valor da compra vira crédito pro cliente)",
        max_digits=5, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Deixe 0 pra desativar o cashback.",
    )

    class Meta:
        verbose_name = "Configuração de fidelidade"
        verbose_name_plural = "Configuração de fidelidade"

    def __str__(self):
        return "Configuração de fidelidade"


def get_config_fidelidade():
    config, _ = ConfiguracaoFidelidade.objects.get_or_create(pk=1)
    return config


class Cliente(models.Model):
    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    documento = CampoCriptografado("CPF/CNPJ", max_length=500, blank=True)
    data_nascimento = models.DateField("Data de nascimento", null=True, blank=True)

    cep = models.CharField(max_length=10, blank=True)
    logradouro = models.CharField(max_length=200, blank=True)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100, blank=True)
    cidade = models.CharField(max_length=100, blank=True)
    uf = models.CharField(max_length=2, blank=True)

    pontos_fidelidade = models.PositiveIntegerField(default=0, editable=False)
    saldo_credito = models.DecimalField(
        "Saldo de crédito/cashback (R$)", max_digits=10, decimal_places=2,
        default=Decimal("0"), editable=False,
    )

    consentimento_dados = models.BooleanField(
        "Consentiu com o uso dos dados (LGPD)", default=False
    )
    consentimento_em = models.DateTimeField(null=True, blank=True)

    blacklist = models.BooleanField("Na lista de restrição", default=False)
    blacklist_motivo = models.CharField(max_length=200, blank=True)

    anonimizado = models.BooleanField(default=False, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self):
        return self.nome

    @property
    def endereco_completo(self):
        partes = [self.logradouro, self.numero, self.bairro, self.cidade, self.uf]
        partes = [p for p in partes if p]
        return ", ".join(partes) if partes else ""

    @property
    def total_gasto(self):
        return sum(
            (v.total for v in self.vendas.filter(status="fechada")), Decimal("0")
        )

    @property
    def numero_compras(self):
        return self.vendas.filter(status="fechada").count()

    @property
    def valor_pontos_em_reais(self):
        config = get_config_fidelidade()
        return self.pontos_fidelidade * config.valor_resgate_ponto


class CupomDesconto(models.Model):
    TIPO_CHOICES = [("percentual", "Percentual (%)"), ("fixo", "Valor fixo (R$)")]

    codigo = models.CharField(max_length=30, unique=True)
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default="percentual")
    valor = models.DecimalField(
        "Valor (% ou R$, conforme o tipo)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    ativo = models.BooleanField(default=True)
    validade = models.DateField(null=True, blank=True, help_text="Deixe em branco pra não expirar.")
    usos_maximos = models.PositiveIntegerField(
        null=True, blank=True, help_text="Deixe em branco pra uso ilimitado."
    )
    usos_atuais = models.PositiveIntegerField(default=0, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cupom de desconto"
        verbose_name_plural = "Cupons de desconto"

    def __str__(self):
        return self.codigo

    @property
    def valido(self):
        if not self.ativo:
            return False
        if self.validade and self.validade < timezone.localdate():
            return False
        if self.usos_maximos is not None and self.usos_atuais >= self.usos_maximos:
            return False
        return True

    def calcular_desconto(self, subtotal):
        if self.tipo == "percentual":
            return min((subtotal * self.valor / 100).quantize(Decimal("0.01")), subtotal)
        return min(self.valor, subtotal)


class Vale(models.Model):
    """Vale-presente/voucher com saldo próprio, usado como forma de pagamento no PDV."""
    codigo = models.CharField(max_length=30, unique=True)
    cliente = models.ForeignKey(
        "Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="vales"
    )
    valor_inicial = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    saldo = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)], blank=True
    )
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Vale"
        verbose_name_plural = "Vales"

    def __str__(self):
        return f"{self.codigo} — saldo R$ {self.saldo}"

    def save(self, *args, **kwargs):
        if self._state.adding and not self.saldo:
            self.saldo = self.valor_inicial
        super().save(*args, **kwargs)

    @property
    def valido(self):
        return self.ativo and self.saldo > 0


class Venda(models.Model):
    """
    Uma venda começa 'aberta' (carrinho em edição no PDV) e é
    'fechada' quando o pagamento é confirmado. É só no fechamento
    que o estoque é baixado e o lançamento financeiro é criado —
    isso evita descontar estoque de vendas que foram canceladas
    antes de finalizar.
    """

    STATUS_CHOICES = [
        ("orcamento", "Orçamento"),
        ("aberta", "Aberta"),
        ("pendente_aprovacao", "Aguardando aprovação de desconto"),
        ("fechada", "Fechada"),
        ("cancelada", "Cancelada"),
    ]

    CANAL_CHOICES = [
        ("fisica", "Loja física"),
        ("online", "Online"),
    ]

    FORMA_PAGAMENTO_CHOICES = [
        ("dinheiro", "Dinheiro"),
        ("pix", "Pix"),
        ("debito", "Cartão de débito"),
        ("credito_avista", "Cartão de crédito à vista"),
        ("credito_parcelado", "Cartão de crédito parcelado"),
        ("vale", "Vale"),
    ]

    cliente = models.ForeignKey(
        Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendas"
    )
    vendedor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="vendas_realizadas",
    )
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES, default="fisica")
    pontos_resgatados = models.PositiveIntegerField(default=0)
    credito_usado = models.DecimalField(
        "Crédito/cashback usado nessa venda (R$)", max_digits=10, decimal_places=2,
        default=Decimal("0"), validators=[MinValueValidator(0)],
    )
    cupom = models.ForeignKey(
        CupomDesconto, on_delete=models.SET_NULL, null=True, blank=True, related_name="vendas"
    )
    mensagem_posvenda_enviada = models.BooleanField(default=False, editable=False)
    mensagem_recuperacao_enviada = models.BooleanField(default=False, editable=False)
    uuid_offline = models.CharField(
        max_length=40, unique=True, null=True, blank=True,
        help_text="Preenchido só quando a venda foi feita no modo offline do PDV — evita duplicar ao sincronizar.",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="aberta")
    forma_pagamento = models.CharField(
        max_length=20, choices=FORMA_PAGAMENTO_CHOICES, blank=True
    )
    parcelas = models.PositiveSmallIntegerField(default=1)
    desconto = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    acrescimo = models.DecimalField(
        "Acréscimo (R$)", max_digits=10, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    observacoes = models.TextField(blank=True)

    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-aberta_em"]

    def __str__(self):
        return f"Venda #{self.pk} — {self.get_status_display()}"

    @property
    def subtotal(self):
        return sum((item.subtotal for item in self.itens.all()), Decimal("0"))

    @property
    def total(self):
        return max(self.subtotal - self.desconto + self.acrescimo, Decimal("0"))


class PagamentoVenda(models.Model):
    """
    Uma "fatia" do pagamento de uma venda. A maioria das vendas tem só
    uma fatia (pagamento único), mas isso permite pagamento misto —
    por exemplo, parte em dinheiro e parte no cartão.
    """
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="pagamentos")
    forma_pagamento = models.CharField(max_length=20, choices=Venda.FORMA_PAGAMENTO_CHOICES)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)]
    )
    parcelas = models.PositiveSmallIntegerField(default=1)
    vale = models.ForeignKey(
        Vale, on_delete=models.PROTECT, null=True, blank=True,
        help_text="Preenchido só quando a forma de pagamento é 'Vale'.",
    )

    class Meta:
        verbose_name = "Pagamento da venda"
        verbose_name_plural = "Pagamentos da venda"

    def __str__(self):
        return f"{self.get_forma_pagamento_display()} — R$ {self.valor}"


class ItemVenda(models.Model):
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    desconto = models.DecimalField(
        "Desconto no item (R$)", max_digits=10, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = "Item da venda"
        verbose_name_plural = "Itens da venda"

    def __str__(self):
        return f"{self.quantidade}x {self.produto.sku}"

    @property
    def subtotal(self):
        return max((self.preco_unitario * self.quantidade) - self.desconto, Decimal("0"))

    @property
    def quantidade_devolvida(self):
        from django.db.models import Sum
        total = ItemDevolucao.objects.filter(
            devolucao__venda=self.venda, produto=self.produto, devolucao__processada=True
        ).aggregate(total=Sum("quantidade"))["total"]
        return total or 0

    @property
    def quantidade_disponivel_devolucao(self):
        return self.quantidade - self.quantidade_devolvida


class Devolucao(models.Model):
    """
    Estorno parcial ou total de uma venda já fechada. Ao ser
    'processada' (ação no admin), o sistema automaticamente:
    - devolve os itens ao estoque
    - estorna o valor no financeiro (caixa se já tinha sido recebido,
      ou reduz/cancela a conta a receber se ainda estava pendente)
    """

    venda = models.ForeignKey(Venda, on_delete=models.PROTECT, related_name="devolucoes")
    motivo = models.CharField(max_length=200, blank=True)
    processada = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    processada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Devolução"
        verbose_name_plural = "Devoluções"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Devolução #{self.pk} — Venda #{self.venda_id}"

    @property
    def total(self):
        return sum(
            (item.quantidade * item.preco_unitario for item in self.itens.all()),
            Decimal("0"),
        )


class ItemDevolucao(models.Model):
    devolucao = models.ForeignKey(Devolucao, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey("catalogo.Produto", on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Item da devolução"
        verbose_name_plural = "Itens da devolução"

    def __str__(self):
        return f"{self.quantidade}x {self.produto.sku}"


class VendaOfflinePendente(models.Model):
    """
    Uma venda feita no modo offline do PDV que NÃO conseguiu ser
    processada ao sincronizar (ex: estoque insuficiente porque outra
    venda já consumiu o que sobrava enquanto essa ficou na fila).
    Fica guardada aqui pra revisão manual — nunca vira uma Venda de
    verdade sozinha.
    """
    uuid_offline = models.CharField(max_length=40, unique=True)
    payload_json = models.TextField()
    erro = models.TextField(blank=True)
    resolvida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Venda offline pendente"
        verbose_name_plural = "Vendas offline pendentes"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"Pendente {self.uuid_offline[:8]} — {'resolvida' if self.resolvida else 'em aberto'}"
