from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class CategoriaFinanceira(models.Model):
    """
    Categoriza receitas e despesas. É o que alimenta o DRE depois
    (ex: 'Venda de cartas', 'Aluguel', 'Frete', 'Compra de estoque').
    """

    TIPO_CHOICES = [("receita", "Receita"), ("despesa", "Despesa")]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)

    class Meta:
        verbose_name = "Categoria financeira"
        verbose_name_plural = "Categorias financeiras"
        unique_together = ("nome", "tipo")
        ordering = ["tipo", "nome"]

    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class ContaReceber(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("recebido", "Recebido"),
        ("cancelado", "Cancelado"),
    ]

    MEIO_PAGAMENTO_CHOICES = [
        ("", "—"),
        ("dinheiro", "Dinheiro"),
        ("pix", "Pix"),
        ("boleto", "Boleto"),
        ("ted", "TED"),
        ("doc", "DOC"),
        ("transferencia", "Transferência bancária"),
        ("cartao", "Cartão"),
        ("cheque", "Cheque"),
        ("outro", "Outro"),
    ]

    descricao = models.CharField(max_length=200)
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True
    )
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="contas_receber",
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira, on_delete=models.PROTECT,
        limit_choices_to={"tipo": "receita"},
    )
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    vencimento = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    data_recebimento = models.DateField(null=True, blank=True)
    forma_pagamento = models.CharField(max_length=30, blank=True)
    meio_pagamento = models.CharField(
        "Meio de pagamento", max_length=15, choices=MEIO_PAGAMENTO_CHOICES, blank=True,
    )
    numero_boleto = models.CharField("Número do boleto / nosso número", max_length=60, blank=True)
    linha_digitavel = models.CharField("Linha digitável", max_length=60, blank=True)
    parcela_numero = models.PositiveSmallIntegerField(default=1)
    parcela_total = models.PositiveSmallIntegerField(default=1)
    grupo_parcelamento = models.CharField(max_length=40, blank=True)
    ultima_cobranca_enviada = models.DateField(null=True, blank=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conta a receber"
        verbose_name_plural = "Contas a receber"
        ordering = ["vencimento"]

    def __str__(self):
        if self.parcela_total > 1:
            return f"{self.descricao} ({self.parcela_numero}/{self.parcela_total}) — R$ {self.valor}"
        return f"{self.descricao} — R$ {self.valor}"

    @property
    def vencida(self):
        from django.utils import timezone
        return self.status == "pendente" and self.vencimento < timezone.localdate()


class ContaPagar(models.Model):
    STATUS_CHOICES = [
        ("pendente", "Pendente"),
        ("pago", "Pago"),
        ("cancelado", "Cancelado"),
    ]

    MEIO_PAGAMENTO_CHOICES = [
        ("", "—"),
        ("dinheiro", "Dinheiro"),
        ("pix", "Pix"),
        ("boleto", "Boleto"),
        ("ted", "TED"),
        ("doc", "DOC"),
        ("transferencia", "Transferência bancária"),
        ("cartao", "Cartão"),
        ("cheque", "Cheque"),
        ("outro", "Outro"),
    ]

    descricao = models.CharField(max_length=200)
    fornecedor = models.CharField(max_length=150, blank=True)
    categoria = models.ForeignKey(
        CategoriaFinanceira, on_delete=models.PROTECT,
        limit_choices_to={"tipo": "despesa"},
    )
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    vencimento = models.DateField()
    recorrente = models.BooleanField(
        "Despesa fixa recorrente (gera a próxima automaticamente ao pagar)", default=False
    )
    proxima_gerada = models.BooleanField(default=False, editable=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pendente")
    data_pagamento = models.DateField(null=True, blank=True)
    meio_pagamento = models.CharField(
        "Meio de pagamento", max_length=15, choices=MEIO_PAGAMENTO_CHOICES, blank=True,
    )
    numero_boleto = models.CharField("Número do boleto / nosso número", max_length=60, blank=True)
    linha_digitavel = models.CharField("Linha digitável", max_length=60, blank=True)
    parcela_numero = models.PositiveSmallIntegerField(default=1)
    parcela_total = models.PositiveSmallIntegerField(default=1)
    grupo_parcelamento = models.CharField(max_length=40, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conta a pagar"
        verbose_name_plural = "Contas a pagar"
        ordering = ["vencimento"]

    def __str__(self):
        if self.parcela_total > 1:
            return f"{self.descricao} ({self.parcela_numero}/{self.parcela_total}) — R$ {self.valor}"
        return f"{self.descricao} — R$ {self.valor}"

    @property
    def vencida(self):
        from django.utils import timezone
        return self.status == "pendente" and self.vencimento < timezone.localdate()


class ContaBancaria(models.Model):
    TIPO_CHOICES = [("corrente", "Conta corrente"), ("poupanca", "Poupança"), ("outra", "Outra")]

    nome = models.CharField(max_length=100, help_text="Como você quer identificar essa conta, ex: 'Nubank PJ'.")
    banco = models.CharField(max_length=100, blank=True)
    agencia = models.CharField(max_length=20, blank=True)
    numero_conta = models.CharField(max_length=30, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default="corrente")
    saldo_inicial = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"), validators=[MinValueValidator(0)]
    )
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Conta bancária"
        verbose_name_plural = "Contas bancárias"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.banco})" if self.banco else self.nome

    @property
    def saldo_atual(self):
        entradas = self.movimentos.filter(tipo="entrada").aggregate(t=models.Sum("valor"))["t"] or Decimal("0")
        saidas = self.movimentos.filter(tipo="saida").aggregate(t=models.Sum("valor"))["t"] or Decimal("0")
        return self.saldo_inicial + entradas - saidas


class ExtratoBancario(models.Model):
    """
    Uma linha do extrato importada de um arquivo OFX do banco.
    Existe separado do MovimentoCaixa porque representa o que o BANCO
    diz que aconteceu — a conciliação é o processo de casar isso com
    o que o SISTEMA registrou. `valor` positivo = crédito, negativo = débito.
    """
    conta_bancaria = models.ForeignKey(ContaBancaria, on_delete=models.CASCADE, related_name="extratos")
    data = models.DateField()
    descricao = models.CharField(max_length=255, blank=True)
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    fitid = models.CharField(
        "Identificador da transação (FITID do OFX)", max_length=100, blank=True,
    )
    conciliado = models.BooleanField(default=False)
    movimento_caixa = models.ForeignKey(
        "MovimentoCaixa", on_delete=models.SET_NULL, null=True, blank=True, related_name="extratos_conciliados"
    )
    importado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Linha de extrato bancário"
        verbose_name_plural = "Extrato bancário"
        ordering = ["-data"]
        unique_together = ("conta_bancaria", "fitid")

    def __str__(self):
        return f"{self.data} — R$ {self.valor} — {self.descricao[:40]}"


class CaixaSessao(models.Model):
    """
    Um "turno" de caixa: abre com um valor de troco, recebe as vendas
    e sangrias/suprimentos do período, e fecha conferindo o valor
    contado contra o saldo esperado pelo sistema.
    """

    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="caixas_abertos"
    )
    valor_abertura = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0"),
        validators=[MinValueValidator(0)],
    )
    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(null=True, blank=True)
    valor_fechamento_informado = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0)],
    )
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = "Sessão de caixa"
        verbose_name_plural = "Sessões de caixa"
        ordering = ["-aberta_em"]

    def __str__(self):
        status = "aberta" if self.fechada_em is None else "fechada"
        return f"Caixa #{self.pk} ({status}) — {self.aberta_por}"

    @property
    def aberta(self):
        return self.fechada_em is None

    @property
    def total_entradas(self):
        return self.movimentos.filter(tipo="entrada").aggregate(
            total=models.Sum("valor"))["total"] or Decimal("0")

    @property
    def total_saidas(self):
        return self.movimentos.filter(tipo="saida").aggregate(
            total=models.Sum("valor"))["total"] or Decimal("0")

    @property
    def saldo_esperado(self):
        return self.valor_abertura + self.total_entradas - self.total_saidas

    @property
    def diferenca(self):
        if self.valor_fechamento_informado is None:
            return None
        return self.valor_fechamento_informado - self.saldo_esperado


class MovimentoCaixa(models.Model):
    """
    Registro real de dinheiro que entrou/saiu do caixa — usado pro
    fluxo de caixa efetivo (diferente do "pendente" das contas a
    pagar/receber, que é apenas previsão).
    """

    TIPO_CHOICES = [("entrada", "Entrada"), ("saida", "Saída")]

    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    valor = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    descricao = models.CharField(max_length=200)
    data = models.DateField()
    sessao = models.ForeignKey(
        CaixaSessao, on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentos"
    )
    conta_receber = models.ForeignKey(
        ContaReceber, on_delete=models.SET_NULL, null=True, blank=True
    )
    conta_pagar = models.ForeignKey(
        ContaPagar, on_delete=models.SET_NULL, null=True, blank=True
    )
    conta_bancaria = models.ForeignKey(
        "ContaBancaria", on_delete=models.SET_NULL, null=True, blank=True, related_name="movimentos"
    )
    conciliado = models.BooleanField(default=False, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimento de caixa"
        verbose_name_plural = "Movimentos de caixa"
        ordering = ["-data", "-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — R$ {self.valor} ({self.data})"


class ConfiguracaoCobranca(models.Model):
    ativo = models.BooleanField("Enviar cobrança automática de conta vencida", default=False)
    dias_apos_vencimento = models.PositiveIntegerField(
        "Enviar a partir de quantos dias vencida", default=3,
    )
    intervalo_entre_cobrancas_dias = models.PositiveIntegerField(
        "Intervalo mínimo entre cobranças da mesma conta (dias)", default=7,
    )
    mensagem = models.TextField(
        default="Oi {nome}! Notei que a conta \"{descricao}\" no valor de R$ {valor} "
                "venceu em {vencimento}. Pode dar uma olhada quando puder? Qualquer dúvida, é só chamar!"
    )

    class Meta:
        verbose_name = "Configuração de cobrança"
        verbose_name_plural = "Configuração de cobrança"

    def __str__(self):
        return "Configuração de cobrança"


def get_config_cobranca():
    config, _ = ConfiguracaoCobranca.objects.get_or_create(pk=1)
    return config
