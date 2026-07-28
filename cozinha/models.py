import uuid
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class CategoriaPrato(models.Model):
    nome = models.CharField(max_length=60)
    ordem_exibicao = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Categoria do cardápio"
        verbose_name_plural = "Categorias do cardápio"
        ordering = ["ordem_exibicao", "nome"]

    def __str__(self):
        return self.nome


class Prato(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    foto = models.ImageField(upload_to="pratos/%Y/%m/", blank=True)
    categoria = models.ForeignKey(
        CategoriaPrato, on_delete=models.SET_NULL, null=True, blank=True, related_name="pratos"
    )
    disponivel = models.BooleanField("Disponível no cardápio agora", default=True)
    tempo_preparo_min = models.PositiveIntegerField(
        "Tempo estimado de preparo (minutos)", default=10
    )
    ordem_exibicao = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Prato"
        verbose_name_plural = "Pratos"
        ordering = ["categoria__ordem_exibicao", "ordem_exibicao", "nome"]

    def __str__(self):
        return f"{self.nome} — R$ {self.preco}"


class Mesa(models.Model):
    """
    Uma mesa física da loja. O token é o que vai no QR code — não o
    número da mesa em si — pra não dar pra adivinhar/manipular a URL
    só trocando um número (ex: /cardapio/mesa/7/ seria fácil de
    forjar; um UUID não).
    """
    numero = models.PositiveIntegerField(unique=True)
    nome = models.CharField(max_length=50, blank=True, help_text="Ex: 'Mesa da janela' (opcional, só número já basta)")
    token_publico = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    ativa = models.BooleanField("Aceitando pedidos", default=True)

    class Meta:
        verbose_name = "Mesa"
        verbose_name_plural = "Mesas"
        ordering = ["numero"]

    def __str__(self):
        return self.nome or f"Mesa {self.numero}"

    @property
    def comanda_aberta(self):
        return self.comandas.filter(status="aberta").first()


class Comanda(models.Model):
    """A 'conta corrente' de uma mesa — acumula os pedidos até fechar no PDV."""
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("fechada", "Fechada"),
        ("cancelada", "Cancelada"),
    ]

    mesa = models.ForeignKey(Mesa, on_delete=models.PROTECT, related_name="comandas")
    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aberta")
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.SET_NULL, null=True, blank=True, related_name="comanda_origem"
    )
    fechada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Comanda"
        verbose_name_plural = "Comandas"
        ordering = ["-aberta_em"]

    def __str__(self):
        return f"Comanda {self.mesa} — {self.get_status_display()}"

    @property
    def valor_total(self):
        return sum(
            (p.valor_total for p in self.pedidos.exclude(status="cancelado")), Decimal("0")
        )

    @property
    def itens_agrupados(self):
        """Junta os itens de todos os pedidos da comanda, somando quantidades do mesmo prato."""
        agrupado = {}
        for pedido in self.pedidos.exclude(status="cancelado"):
            for item in pedido.itens.all():
                chave = item.prato_id
                if chave not in agrupado:
                    agrupado[chave] = {"prato": item.prato, "quantidade": 0, "subtotal": Decimal("0")}
                agrupado[chave]["quantidade"] += item.quantidade
                agrupado[chave]["subtotal"] += item.subtotal
        return list(agrupado.values())


class ChamadoAtendente(models.Model):
    TIPO_CHOICES = [
        ("atendente", "Chamar atendente"),
        ("talheres", "Pedir talheres"),
        ("guardanapo", "Pedir guardanapo"),
        ("gelo", "Pedir gelo"),
        ("fechamento", "Solicitar fechamento da conta"),
    ]
    mesa = models.ForeignKey(Mesa, on_delete=models.CASCADE, related_name="chamados")
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default="atendente")
    atendido = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)
    atendido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Chamado"
        verbose_name_plural = "Chamados"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} — {self.mesa} ({'atendido' if self.atendido else 'pendente'})"


class PedidoCozinha(models.Model):
    STATUS_CHOICES = [
        ("recebido", "Recebido"),
        ("em_preparo", "Em preparo"),
        ("pronto", "Pronto"),
        ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ]
    PRIORIDADE_CHOICES = [
        (1, "Normal"),
        (2, "Alta"),
        (3, "Urgente"),
    ]

    codigo_acompanhamento = models.CharField(max_length=40, unique=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_cozinha"
    )
    nome_para_chamar = models.CharField(
        "Nome (pra chamar quando ficar pronto)", max_length=80, blank=True
    )
    mesa_ou_local = models.CharField(max_length=40, blank=True, help_text="Ex: Mesa 3, Balcão, Retirada")
    mesa = models.ForeignKey(
        Mesa, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_diretos",
        help_text="Preenchido sozinho quando o pedido vem do QR code de uma mesa específica.",
    )
    comanda = models.ForeignKey(
        Comanda, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos"
    )
    ip = models.CharField(max_length=45, blank=True, editable=False)
    dispositivo = models.CharField(max_length=255, blank=True, editable=False)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="recebido")
    prioridade = models.PositiveSmallIntegerField(choices=PRIORIDADE_CHOICES, default=1)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    em_preparo_em = models.DateTimeField(null=True, blank=True)
    pronto_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    atendido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Pedido da cozinha"
        verbose_name_plural = "Pedidos da cozinha"
        ordering = ["-prioridade", "criado_em"]

    def __str__(self):
        quem = self.nome_para_chamar or (self.cliente.nome if self.cliente else "Cliente")
        return f"Pedido #{self.pk} — {quem} ({self.get_status_display()})"

    @property
    def valor_total(self):
        return sum((item.subtotal for item in self.itens.all()), Decimal("0"))

    @property
    def tempo_espera_minutos(self):
        referencia = self.entregue_em or timezone.now()
        return int((referencia - self.criado_em).total_seconds() // 60)

    def avancar_status(self):
        """Move pro próximo status da esteira (recebido -> em_preparo -> pronto -> entregue)."""
        agora = timezone.now()
        if self.status == "recebido":
            self.status = "em_preparo"
            self.em_preparo_em = agora
        elif self.status == "em_preparo":
            self.status = "pronto"
            self.pronto_em = agora
        elif self.status == "pronto":
            self.status = "entregue"
            self.entregue_em = agora
        self.save()


class ItemPedidoCozinha(models.Model):
    pedido = models.ForeignKey(PedidoCozinha, on_delete=models.CASCADE, related_name="itens")
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    observacao = models.CharField("Observação (ex: sem cebola)", max_length=200, blank=True)

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantidade}x {self.prato.nome}"

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario
