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


class EstacaoProducao(models.Model):
    nome = models.CharField(max_length=60, unique=True)
    icone = models.CharField(max_length=12, blank=True, default="🍳")
    cor = models.CharField(max_length=7, default="#7c3aed", help_text="Cor hexadecimal, ex.: #7c3aed")
    ativa = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Estação de produção"
        verbose_name_plural = "Estações de produção"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return f"{self.icone} {self.nome}".strip()


class Prato(models.Model):
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    foto = models.ImageField(upload_to="pratos/%Y/%m/", blank=True)
    categoria = models.ForeignKey(
        CategoriaPrato, on_delete=models.SET_NULL, null=True, blank=True, related_name="pratos"
    )
    estacao = models.ForeignKey(
        EstacaoProducao,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pratos",
        help_text="Estação responsável por preparar este item.",
    )
    instrucoes_preparo = models.TextField(
        "Instruções rápidas de preparo",
        blank=True,
        help_text="Ex.: grelhar hambúrguer, aquecer pão, montar e embalar.",
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


class EtapaPreparo(models.Model):
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE, related_name="etapas_preparo")
    descricao = models.CharField(max_length=180)
    ordem = models.PositiveIntegerField(default=0)
    obrigatoria = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Etapa de preparo"
        verbose_name_plural = "Etapas de preparo"
        ordering = ["ordem", "id"]

    def __str__(self):
        return f"{self.prato.nome}: {self.descricao}"


class Mesa(models.Model):
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


class FechamentoComanda(models.Model):
    """
    Cada parte de um fechamento de comanda vira um registro aqui — se
    fechar tudo junto, é um registro só; se dividir a conta, é um
    registro por parte/pessoa. Cada um gera uma Venda de verdade.
    """
    comanda = models.ForeignKey("Comanda", on_delete=models.CASCADE, related_name="fechamentos")
    venda = models.ForeignKey("vendas.Venda", on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.CharField(max_length=120, blank=True, help_text="Ex: 'Parte 1 de 3' ou o nome da pessoa")
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fechamento da comanda"
        verbose_name_plural = "Fechamentos da comanda"
        ordering = ["criado_em"]

    def __str__(self):
        return f"{self.comanda.mesa} — {self.descricao or 'fechamento'} — R$ {self.valor}"


class Comanda(models.Model):
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
        return sum((p.valor_total for p in self.pedidos.exclude(status="cancelado")), Decimal("0"))

    @property
    def itens_agrupados(self):
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
        ("em_entrega", "Em entrega"),
        ("entregue", "Entregue"),
        ("cancelado", "Cancelado"),
    ]
    PRIORIDADE_CHOICES = [(1, "Normal"), (2, "Alta"), (3, "Urgente")]

    codigo_acompanhamento = models.CharField(max_length=40, unique=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_cozinha"
    )
    participante = models.ForeignKey(
        "ParticipanteMesa", on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos"
    )
    nome_para_chamar = models.CharField("Nome (pra chamar quando ficar pronto)", max_length=80, blank=True)
    mesa_ou_local = models.CharField(max_length=40, blank=True, help_text="Ex: Mesa 3, Balcão, Retirada")
    mesa = models.ForeignKey(
        Mesa, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos_diretos",
        help_text="Preenchido sozinho quando o pedido vem do QR code de uma mesa específica.",
    )
    comanda = models.ForeignKey(Comanda, on_delete=models.SET_NULL, null=True, blank=True, related_name="pedidos")
    ip = models.CharField(max_length=45, blank=True, editable=False)
    dispositivo = models.CharField(max_length=255, blank=True, editable=False)
    status = models.CharField(max_length=12, choices=STATUS_CHOICES, default="recebido")
    prioridade = models.PositiveSmallIntegerField(choices=PRIORIDADE_CHOICES, default=1)
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    em_preparo_em = models.DateTimeField(null=True, blank=True)
    pronto_em = models.DateTimeField(null=True, blank=True)
    em_entrega_em = models.DateTimeField(null=True, blank=True)
    entregue_em = models.DateTimeField(null=True, blank=True)
    atendido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

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
        return max(int((referencia - self.criado_em).total_seconds() // 60), 0)

    @property
    def tempo_estimado_minutos(self):
        tempos = [item.prato.tempo_preparo_min for item in self.itens.all()]
        return max(tempos, default=10)

    @property
    def nivel_atraso(self):
        espera = self.tempo_espera_minutos
        estimado = self.tempo_estimado_minutos
        if espera > estimado + 5:
            return "critico"
        if espera > estimado:
            return "atrasado"
        if espera >= max(estimado - 3, 1):
            return "atencao"
        return "normal"

    @property
    def progresso_percentual(self):
        itens = list(self.itens.all())
        if not itens:
            return 0
        total = sum(max(item.checklist.count(), 1) for item in itens)
        concluidas = 0
        for item in itens:
            if item.checklist.exists():
                concluidas += item.checklist.filter(concluido=True).count()
            elif item.preparo_concluido:
                concluidas += 1
        return int((concluidas / total) * 100) if total else 0

    def avancar_status(self):
        agora = timezone.now()
        if self.status == "recebido":
            self.status = "em_preparo"
            self.em_preparo_em = agora
            self.itens.filter(iniciado_em__isnull=True).update(iniciado_em=agora)
        elif self.status == "em_preparo":
            self.status = "pronto"
            self.pronto_em = agora
            self.itens.filter(concluido_em__isnull=True).update(preparo_concluido=True, concluido_em=agora)
        elif self.status == "pronto":
            self.status = "em_entrega"
            self.em_entrega_em = agora
        elif self.status == "em_entrega":
            self.status = "entregue"
            self.entregue_em = agora
        self.save()


class AdicionalPrato(models.Model):
    """Um extra opcional que pode ser adicionado a um prato, com preço próprio (ex: bacon +R$4)."""
    prato = models.ForeignKey(Prato, on_delete=models.CASCADE, related_name="adicionais")
    nome = models.CharField(max_length=80)
    preco_extra = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    disponivel = models.BooleanField(default=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Adicional do prato"
        verbose_name_plural = "Adicionais do prato"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return f"{self.prato.nome} — {self.nome} (+R$ {self.preco_extra})"


class ItemPedidoCozinha(models.Model):
    pedido = models.ForeignKey(PedidoCozinha, on_delete=models.CASCADE, related_name="itens")
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    observacao = models.CharField("Observação (ex: sem cebola)", max_length=200, blank=True)
    preparo_concluido = models.BooleanField(default=False)
    iniciado_em = models.DateTimeField(null=True, blank=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Item do pedido"
        verbose_name_plural = "Itens do pedido"

    def __str__(self):
        return f"{self.quantidade}x {self.prato.nome}"

    @property
    def preco_adicionais_unitario(self):
        return sum((a.preco_extra for a in self.adicionais_escolhidos.all()), Decimal("0"))

    @property
    def subtotal(self):
        return self.quantidade * (self.preco_unitario + self.preco_adicionais_unitario)

    @property
    def estacao(self):
        return self.prato.estacao


class ItemPedidoAdicional(models.Model):
    """
    Guarda o adicional escolhido num item do pedido, com nome e preço
    'congelados' no momento do pedido — assim, se o preço do adicional
    mudar depois no cardápio, o pedido antigo continua mostrando o
    valor que o cliente realmente pagou.
    """
    item_pedido = models.ForeignKey(ItemPedidoCozinha, on_delete=models.CASCADE, related_name="adicionais_escolhidos")
    adicional = models.ForeignKey(AdicionalPrato, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=80)
    preco_extra = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        verbose_name = "Adicional escolhido"
        verbose_name_plural = "Adicionais escolhidos"

    def __str__(self):
        return f"{self.nome} (+R$ {self.preco_extra})"


class ChecklistItemProducao(models.Model):
    item_pedido = models.ForeignKey(ItemPedidoCozinha, on_delete=models.CASCADE, related_name="checklist")
    descricao = models.CharField(max_length=180)
    ordem = models.PositiveIntegerField(default=0)
    obrigatoria = models.BooleanField(default=True)
    concluido = models.BooleanField(default=False)
    concluido_em = models.DateTimeField(null=True, blank=True)
    concluido_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Item do checklist de produção"
        verbose_name_plural = "Checklist de produção"
        ordering = ["ordem", "id"]

    def __str__(self):
        return self.descricao


class HistoricoStatusPedido(models.Model):
    pedido = models.ForeignKey(PedidoCozinha, on_delete=models.CASCADE, related_name="historico_status")
    status_anterior = models.CharField(max_length=12, blank=True)
    status_novo = models.CharField(max_length=12)
    alterado_em = models.DateTimeField(auto_now_add=True)
    alterado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Histórico de status do pedido"
        verbose_name_plural = "Históricos de status dos pedidos"
        ordering = ["-alterado_em"]

    def __str__(self):
        return f"Pedido #{self.pedido_id}: {self.status_anterior} → {self.status_novo}"


class ParticipanteMesa(models.Model):
    comanda = models.ForeignKey(Comanda, on_delete=models.CASCADE, related_name="participantes")
    nome = models.CharField(max_length=80)
    token_dispositivo = models.UUIDField(default=uuid.uuid4, db_index=True)
    entrou_em = models.DateTimeField(auto_now_add=True)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Jogador/cliente da mesa"
        verbose_name_plural = "Jogadores/clientes da mesa"
        constraints = [models.UniqueConstraint(fields=["comanda", "token_dispositivo"], name="uniq_participante_dispositivo_comanda")]

    def __str__(self):
        return f"{self.nome} — {self.comanda.mesa}"

    @property
    def total_consumido(self):
        return sum((p.valor_total for p in self.pedidos.exclude(status="cancelado")), Decimal("0"))


class PromocaoCardapio(models.Model):
    titulo = models.CharField(max_length=120)
    descricao = models.CharField(max_length=240, blank=True)
    preco_promocional = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    imagem = models.ImageField(upload_to="promocoes/%Y/%m/", blank=True)
    ativa = models.BooleanField(default=True)
    destaque = models.BooleanField(default=True)
    inicio = models.DateTimeField(null=True, blank=True)
    fim = models.DateTimeField(null=True, blank=True)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Promoção do cardápio"
        verbose_name_plural = "Promoções do cardápio"
        ordering = ["ordem", "titulo"]

    def __str__(self):
        return self.titulo

    @property
    def disponivel_agora(self):
        agora = timezone.now()
        return self.ativa and (not self.inicio or self.inicio <= agora) and (not self.fim or self.fim >= agora)


class ItemPromocao(models.Model):
    promocao = models.ForeignKey(PromocaoCardapio, on_delete=models.CASCADE, related_name="itens")
    prato = models.ForeignKey(Prato, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Item da promoção"
        verbose_name_plural = "Itens da promoção"

    def __str__(self):
        return f"{self.quantidade}x {self.prato.nome}"


class AvaliacaoMesa(models.Model):
    comanda = models.ForeignKey(Comanda, on_delete=models.CASCADE, related_name="avaliacoes")
    participante = models.ForeignKey(ParticipanteMesa, on_delete=models.SET_NULL, null=True, blank=True, related_name="avaliacoes")
    pedido = models.ForeignKey(PedidoCozinha, on_delete=models.SET_NULL, null=True, blank=True, related_name="avaliacoes")
    nota_comida = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    nota_atendimento = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    comentario = models.CharField(max_length=500, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Avaliação da mesa"
        verbose_name_plural = "Avaliações das mesas"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Avaliação {self.comanda.mesa} — comida {self.nota_comida}/5, atendimento {self.nota_atendimento}/5"
