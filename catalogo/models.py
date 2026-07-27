from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.core.validators import MinValueValidator


class Categoria(models.Model):
    """Categoria do produto, ex: Pokémon, Yu-Gi-Oh, Magic, Acessórios."""

    JOGO_TCG_CHOICES = [
        ("", "Nenhum (não busca imagem automática)"),
        ("pokemon", "Pokémon"),
        ("magic", "Magic: The Gathering"),
        ("yugioh", "Yu-Gi-Oh!"),
    ]

    nome = models.CharField(max_length=100, unique=True)
    jogo_tcg = models.CharField(
        "Jogo (pra busca automática de imagem)", max_length=10, choices=JOGO_TCG_CHOICES, blank=True,
        help_text="Se marcado, produtos dessa categoria ganham o botão de buscar imagem automaticamente.",
    )

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Subcategoria(models.Model):
    """Subcategoria dentro de uma categoria, ex: Categoria 'Pokémon' -> Subcategoria 'Booster'."""
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name="subcategorias")
    nome = models.CharField(max_length=100)

    class Meta:
        verbose_name = "Subcategoria"
        verbose_name_plural = "Subcategorias"
        unique_together = ("categoria", "nome")
        ordering = ["categoria__nome", "nome"]

    def __str__(self):
        return f"{self.categoria.nome} › {self.nome}"


class Tag(models.Model):
    nome = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name = "Tag"
        verbose_name_plural = "Tags"
        ordering = ["nome"]

    def __str__(self):
        return self.nome


class Produto(models.Model):
    """
    Cada carta/item é cadastrado individualmente com SKU próprio.
    O estoque_atual é mantido automaticamente pelas movimentações
    (venda no PDV baixa estoque, entrada manual soma estoque).
    """

    ESTADO_CONSERVACAO_CHOICES = [
        ("mint", "Mint (M)"),
        ("near_mint", "Near Mint (NM)"),
        ("excellent", "Excellent (EX)"),
        ("good", "Good (GD)"),
        ("light_played", "Light Played (LP)"),
        ("played", "Played (PL)"),
        ("poor", "Poor (PO)"),
        ("na", "Não se aplica"),
    ]

    GRADING_EMPRESA_CHOICES = [
        ("", "Sem grading"),
        ("PSA", "PSA"),
        ("BGS", "BGS (Beckett)"),
        ("CGC", "CGC"),
        ("SGC", "SGC"),
    ]

    IDIOMA_CHOICES = [
        ("pt", "Português"),
        ("en", "Inglês"),
        ("jp", "Japonês"),
        ("es", "Espanhol"),
        ("outro", "Outro"),
    ]

    TIPO_COMPOSICAO_CHOICES = [
        ("simples", "Produto simples (não composto)"),
        ("kit", "Kit"),
        ("combo", "Combo"),
        ("bundle", "Bundle"),
        ("caixa", "Caixa"),
        ("booster_box", "Booster Box"),
        ("blister", "Blister"),
        ("etb", "ETB (Elite Trainer Box)"),
        ("case", "Case"),
    ]

    sku = models.CharField("SKU / código", max_length=50, unique=True)
    codigo_interno = models.CharField(
        "Código interno", max_length=50, blank=True,
        help_text="Código próprio de organização interna, separado do SKU (opcional).",
    )
    codigo_barras = models.CharField(
        "Código de barras (interno/impresso)", max_length=50, blank=True, null=True, unique=True,
    )
    ean = models.CharField(
        "EAN de fábrica", max_length=20, blank=True, null=True, unique=True,
        help_text="Código EAN original do fabricante, quando existir.",
    )
    nome = models.CharField("Nome do item", max_length=200)
    marca = models.CharField("Marca", max_length=100, blank=True)
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="produtos"
    )
    subcategoria = models.ForeignKey(
        Subcategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name="produtos"
    )
    fornecedor = models.ForeignKey(
        "suprimentos.Fornecedor", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="produtos_catalogo", help_text="Fornecedor padrão desse item.",
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="produtos")
    edicao = models.CharField("Edição / coleção", max_length=120, blank=True)
    numero_colecao = models.CharField(
        "Número na coleção", max_length=20, blank=True,
        help_text="Ex: 025/198 — o número impresso na carta dentro do set.",
    )
    idioma = models.CharField(max_length=10, choices=IDIOMA_CHOICES, blank=True)
    raridade = models.CharField("Raridade", max_length=80, blank=True)
    foil = models.BooleanField("Foil", default=False)
    reverse_holo = models.BooleanField("Reverse holo", default=False)
    promo = models.BooleanField("Promo", default=False)
    estado_conservacao = models.CharField(
        max_length=20, choices=ESTADO_CONSERVACAO_CHOICES, default="na"
    )
    descricao = models.TextField("Descrição", blank=True)
    imagem = models.ImageField("Imagem", upload_to="produtos/%Y/%m/", blank=True, null=True)
    peso_gramas = models.PositiveIntegerField("Peso (g)", null=True, blank=True)
    comprimento_cm = models.DecimalField(
        "Comprimento (cm)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    largura_cm = models.DecimalField(
        "Largura (cm)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    altura_cm = models.DecimalField(
        "Altura (cm)", max_digits=6, decimal_places=1, null=True, blank=True
    )
    grading_empresa = models.CharField(
        "Empresa de grading", max_length=10, choices=GRADING_EMPRESA_CHOICES, blank=True
    )
    grading_nota = models.DecimalField(
        "Nota do grading", max_digits=3, decimal_places=1, null=True, blank=True,
        help_text="Ex: 9.5, 10.0",
    )
    grading_certificado = models.CharField(
        "Número do certificado/slab", max_length=50, blank=True
    )

    preco_custo = models.DecimalField(
        "Preço de custo", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)], default=0,
    )
    custo_frete = models.DecimalField(
        "Custo de frete (rateado, R$)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)], default=0,
    )
    custo_impostos = models.DecimalField(
        "Impostos (R$)", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)], default=0,
    )
    preco_venda = models.DecimalField(
        "Preço de venda", max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    preco_minimo = models.DecimalField(
        "Preço mínimo de venda (R$)", max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Alerta no PDV se tentar vender abaixo desse valor.",
    )
    preco_maximo = models.DecimalField(
        "Preço máximo de venda (R$)", max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
        help_text="Referência de teto — útil pra cartas com preço muito volátil.",
    )
    margem_desejada = models.DecimalField(
        "Margem desejada (%)", max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Preencha pra calcular o preço de venda sugerido automaticamente a partir do custo.",
    )

    estoque_atual = models.PositiveIntegerField(default=0, editable=False)
    estoque_minimo = models.PositiveIntegerField(
        "Estoque mínimo (alerta)", default=1
    )
    estoque_maximo = models.PositiveIntegerField(
        "Estoque máximo", null=True, blank=True,
        help_text="Referência de capacidade ideal — não bloqueia entradas.",
    )
    localizacao = models.CharField(
        "Localização física", max_length=100, blank=True,
        help_text="Ex: Prateleira A3, Gaveta 2.",
    )
    lote = models.CharField("Lote", max_length=60, blank=True)
    validade = models.DateField("Data de validade", null=True, blank=True)
    numero_serie = models.CharField("Número de série", max_length=100, blank=True)

    tipo_composicao = models.CharField(
        max_length=20, choices=TIPO_COMPOSICAO_CHOICES, default="simples",
        help_text="Só informativo pra produtos simples. Pra produto composto de verdade, cadastre os componentes abaixo.",
    )
    componentes = models.ManyToManyField(
        "self", through="ComponenteProduto", through_fields=("produto_pai", "produto_componente"),
        symmetrical=False, related_name="usado_em_composicoes", blank=True,
    )

    ativo = models.BooleanField(default=True)
    alerta_estoque_enviado = models.BooleanField(default=False, editable=False)
    codigo_olist = models.CharField(
        "Código no Olist (referência de integração)",
        max_length=60, blank=True, null=True,
    )

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"
        ordering = ["nome"]

    def __str__(self):
        return f"{self.nome} ({self.sku})"

    @property
    def estoque_baixo(self):
        return self.estoque_atual <= self.estoque_minimo

    @property
    def estoque_reservado(self):
        from django.utils import timezone
        hoje = timezone.localdate()
        return self.reservas.filter(status="ativa").filter(
            Q(validade__isnull=True) | Q(validade__gte=hoje)
        ).aggregate(total=Sum("quantidade"))["total"] or 0

    @property
    def estoque_disponivel(self):
        return max(self.estoque_atual - self.estoque_reservado, 0)

    @property
    def grading_display(self):
        if not self.grading_empresa:
            return None
        nota = f" {self.grading_nota}" if self.grading_nota is not None else ""
        return f"{self.grading_empresa}{nota}"

    @property
    def variante_display(self):
        """Junta foil/reverse/promo numa etiqueta curta, ex: 'Foil · Promo'."""
        partes = []
        if self.foil:
            partes.append("Foil")
        if self.reverse_holo:
            partes.append("Reverse Holo")
        if self.promo:
            partes.append("Promo")
        return " · ".join(partes) if partes else None

    @property
    def preco_medio_venda(self):
        """Preço médio praticado de verdade nas vendas fechadas (não o preço de tabela)."""
        from django.db.models import Avg
        media = self.itemvenda_set.filter(venda__status="fechada").aggregate(m=Avg("preco_unitario"))["m"]
        return media

    @property
    def custo_total(self):
        """Custo de aquisição + frete rateado + impostos — base real pro cálculo de margem."""
        return self.preco_custo + self.custo_frete + self.custo_impostos

    @property
    def margem(self):
        if self.custo_total == 0:
            return None
        return self.preco_venda - self.custo_total

    @property
    def lucro(self):
        """Alias de margem em R$ — mesma conta, nome mais comum no varejo."""
        return self.margem

    @property
    def markup_percentual(self):
        if not self.custo_total:
            return None
        return ((self.preco_venda - self.custo_total) / self.custo_total * 100).quantize(Decimal("0.1"))

    @property
    def preco_sugerido(self):
        if self.margem_desejada is None or self.margem_desejada <= 0:
            return None
        return (self.custo_total * (1 + self.margem_desejada / 100)).quantize(Decimal("0.01"))

    @property
    def e_composto(self):
        return self.componentes_kit.exists()

    @property
    def dimensoes_display(self):
        partes = [self.comprimento_cm, self.largura_cm, self.altura_cm]
        if not all(partes):
            return None
        return f"{self.comprimento_cm} × {self.largura_cm} × {self.altura_cm} cm"


class ComponenteProduto(models.Model):
    """
    Relação de "receita" (bill of materials) pra produtos compostos —
    ex: uma Booster Box (produto_pai) é composta por 36 unidades do
    produto_componente Booster. Usado pelas ações de montar/desmontar
    estoque (ver catalogo/services.py).
    """
    produto_pai = models.ForeignKey(
        Produto, on_delete=models.CASCADE, related_name="componentes_kit"
    )
    produto_componente = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="parte_de_composicoes"
    )
    quantidade = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Componente do produto"
        verbose_name_plural = "Componentes do produto"
        unique_together = ("produto_pai", "produto_componente")

    def __str__(self):
        return f"{self.quantidade}x {self.produto_componente.sku} em {self.produto_pai.sku}"


class MovimentacaoEstoque(models.Model):
    """
    Histórico de toda entrada/saída de estoque.
    Nunca editar estoque_atual diretamente no Produto — sempre
    criar uma movimentação, que atualiza o saldo via signal.
    """

    TIPO_CHOICES = [
        ("entrada", "Entrada"),
        ("saida", "Saída"),
        ("ajuste", "Ajuste manual"),
    ]

    CATEGORIA_CHOICES = [
        ("", "—"),
        ("perda", "Perda"),
        ("quebra", "Quebra"),
        ("dano", "Produto danificado"),
        ("roubo", "Roubo/furto"),
        ("vencido", "Vencido"),
        ("outro", "Outro motivo de baixa"),
    ]

    produto = models.ForeignKey(
        Produto, on_delete=models.PROTECT, related_name="movimentacoes"
    )
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    categoria = models.CharField(
        "Categoria (só pra baixas de perda/quebra/dano)",
        max_length=10, choices=CATEGORIA_CHOICES, blank=True,
    )
    quantidade = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200, blank=True)
    venda = models.ForeignKey(
        "vendas.Venda", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="movimentacoes_estoque",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação de estoque"
        verbose_name_plural = "Movimentações de estoque"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"{self.get_tipo_display()} de {self.quantidade}x {self.produto.sku}"


class InventarioSessao(models.Model):
    """
    Uma "sessão" de conferência física de estoque: abre (opcionalmente
    filtrada por categoria), tira uma foto da quantidade que o sistema
    acha que tem de cada produto, e depois compara com o que foi
    contado de verdade. Ao finalizar, ajusta o estoque automaticamente
    onde houver diferença.
    """
    aberta_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="inventarios_abertos"
    )
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Deixe em branco pra conferir todos os produtos ativos.",
    )
    observacoes = models.TextField(blank=True)
    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Sessão de inventário"
        verbose_name_plural = "Sessões de inventário"
        ordering = ["-aberta_em"]

    def __str__(self):
        status = "aberta" if self.fechada_em is None else "fechada"
        return f"Inventário #{self.pk} ({status}) — {self.aberta_por}"

    @property
    def aberta(self):
        return self.fechada_em is None

    @property
    def total_itens(self):
        return self.itens.count()

    @property
    def total_contados(self):
        return self.itens.filter(quantidade_contada__isnull=False).count()

    @property
    def total_divergentes(self):
        return sum(1 for item in self.itens.all() if item.divergente)


class ItemInventario(models.Model):
    sessao = models.ForeignKey(InventarioSessao, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_inventario")
    quantidade_esperada = models.PositiveIntegerField()
    quantidade_contada = models.PositiveIntegerField(null=True, blank=True)
    contado_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Item de inventário"
        verbose_name_plural = "Itens de inventário"
        unique_together = ("sessao", "produto")

    def __str__(self):
        return f"{self.produto.sku} — esperado {self.quantidade_esperada}"

    @property
    def diferenca(self):
        if self.quantidade_contada is None:
            return None
        return self.quantidade_contada - self.quantidade_esperada

    @property
    def divergente(self):
        return self.diferenca is not None and self.diferenca != 0


class Reserva(models.Model):
    """Segura uma quantidade de estoque pra um cliente, sem vender ainda."""

    STATUS_CHOICES = [
        ("ativa", "Ativa"),
        ("atendida", "Atendida (virou venda)"),
        ("cancelada", "Cancelada"),
    ]

    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="reservas")
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="reservas"
    )
    quantidade = models.PositiveIntegerField(default=1)
    validade = models.DateField(
        "Reservado até", null=True, blank=True,
        help_text="Deixe em branco pra reserva sem prazo. Depois dessa data, ela deixa de contar como estoque reservado.",
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="ativa")
    observacoes = models.TextField(blank=True)
    criada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"{self.quantidade}x {self.produto.sku} — {self.get_status_display()}"

    @property
    def expirada(self):
        from django.utils import timezone
        return (
            self.status == "ativa" and self.validade is not None
            and self.validade < timezone.localdate()
        )

    @property
    def vale_como_estoque_reservado(self):
        return self.status == "ativa" and not self.expirada


class HistoricoPreco(models.Model):
    """Registro de toda mudança no preço de venda de um produto — pra acompanhar a evolução ao longo do tempo."""
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE, related_name="historico_precos")
    preco_anterior = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    preco_novo = models.DecimalField(max_digits=10, decimal_places=2)
    alterado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Histórico de preço"
        verbose_name_plural = "Histórico de preços"
        ordering = ["-alterado_em"]

    def __str__(self):
        return f"{self.produto.sku}: R$ {self.preco_anterior} → R$ {self.preco_novo} ({self.alterado_em:%d/%m/%Y})"
