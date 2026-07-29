from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Lead(models.Model):
    """Prospect — pessoa que ainda não é (ou pode não virar) cliente."""

    ORIGEM_CHOICES = [
        ("indicacao", "Indicação"),
        ("redes_sociais", "Redes sociais"),
        ("loja_fisica", "Loja física"),
        ("evento", "Evento/torneio"),
        ("site", "Site/online"),
        ("outro", "Outro"),
    ]

    ETAPA_CHOICES = [
        ("novo", "Novo lead"),
        ("contato", "Em contato"),
        ("negociacao", "Negociação"),
        ("ganho", "Ganho"),
        ("perdido", "Perdido"),
    ]

    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    origem = models.CharField(max_length=20, choices=ORIGEM_CHOICES, default="outro")
    etapa = models.CharField(max_length=15, choices=ETAPA_CHOICES, default="novo")
    valor_estimado = models.DecimalField(
        "Valor estimado do negócio (R$)", max_digits=10, decimal_places=2,
        default=Decimal("0"), validators=[MinValueValidator(0)],
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="leads"
    )
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="leads_origem",
        help_text="Preenchido automaticamente quando o lead é convertido em cliente.",
    )
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        ordering = ["-atualizado_em"]

    def __str__(self):
        return self.nome

    @property
    def ultima_interacao(self):
        return self.interacoes.order_by("-criada_em").first()

    @property
    def dias_sem_interacao(self):
        from django.utils import timezone
        ultima = self.ultima_interacao
        referencia = ultima.criada_em if ultima else self.criado_em
        return (timezone.now() - referencia).days


class InteracaoContato(models.Model):
    TIPO_CHOICES = [
        ("ligacao", "Ligação"),
        ("whatsapp", "WhatsApp"),
        ("email", "E-mail"),
        ("presencial", "Presencial"),
        ("outro", "Outro"),
    ]

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True, related_name="interacoes")
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.CASCADE, null=True, blank=True, related_name="interacoes"
    )
    tipo = models.CharField(max_length=12, choices=TIPO_CHOICES, default="outro")
    descricao = models.TextField(blank=True)
    criada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Interação de contato"
        verbose_name_plural = "Interações de contato"
        ordering = ["-criada_em"]

    def __str__(self):
        alvo = self.lead.nome if self.lead else (self.cliente.nome if self.cliente else "—")
        return f"{self.get_tipo_display()} — {alvo}"


class CategoriaTarefa(models.Model):
    """Uma categoria colorida pra organizar a agenda visualmente (ex: Pagamentos, Eventos, Fornecedores)."""
    nome = models.CharField(max_length=60)
    cor = models.CharField(
        max_length=7, default="#8b6cf2",
        help_text="Código da cor em hexadecimal, ex: #8b6cf2 (pode copiar de um seletor de cor online)",
    )
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Categoria da agenda"
        verbose_name_plural = "Categorias da agenda"
        ordering = ["ordem", "nome"]

    def __str__(self):
        return self.nome


class Tarefa(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    categoria = models.ForeignKey(
        CategoriaTarefa, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas"
    )
    responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="tarefas"
    )
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True, related_name="tarefas")
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.CASCADE, null=True, blank=True, related_name="tarefas"
    )
    data_vencimento = models.DateTimeField()
    concluida = models.BooleanField(default=False)
    concluida_em = models.DateTimeField(null=True, blank=True)
    gerada_automaticamente = models.BooleanField(default=False, editable=False)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tarefa"
        verbose_name_plural = "Tarefas"
        ordering = ["data_vencimento"]

    def __str__(self):
        return self.titulo

    @property
    def atrasada(self):
        from django.utils import timezone
        return not self.concluida and self.data_vencimento < timezone.now()


class Proposta(models.Model):
    STATUS_CHOICES = [
        ("aberta", "Aberta"),
        ("aceita", "Aceita"),
        ("recusada", "Recusada"),
        ("expirada", "Expirada"),
    ]

    titulo = models.CharField(max_length=200)
    descricao = models.TextField(blank=True)
    lead = models.ForeignKey(Lead, on_delete=models.SET_NULL, null=True, blank=True, related_name="propostas")
    cliente = models.ForeignKey(
        "vendas.Cliente", on_delete=models.SET_NULL, null=True, blank=True, related_name="propostas"
    )
    valor = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    validade = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="aberta")
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Proposta"
        verbose_name_plural = "Propostas"
        ordering = ["-criada_em"]

    def __str__(self):
        return f"{self.titulo} — R$ {self.valor}"

    @property
    def expirada(self):
        from django.utils import timezone
        return self.status == "aberta" and self.validade and self.validade < timezone.localdate()


class ConfiguracaoCRM(models.Model):
    posvenda_ativo = models.BooleanField("Enviar mensagem de pós-venda automaticamente", default=False)
    posvenda_dias = models.PositiveIntegerField("Dias após a venda", default=7)
    posvenda_mensagem = models.TextField(
        default="Oi {nome}! Passando pra saber se você curtiu sua compra na Belletti Cards Universe. "
                "Qualquer coisa, é só chamar! 🎴"
    )

    aniversario_ativo = models.BooleanField("Enviar mensagem de aniversário automaticamente", default=False)
    aniversario_mensagem = models.TextField(
        default="Feliz aniversário, {nome}! 🎉 A Belletti Cards Universe deseja um dia incrível pra você!"
    )

    lead_parado_ativo = models.BooleanField("Criar tarefa automática pra lead parado", default=False)
    lead_parado_dias = models.PositiveIntegerField("Dias sem interação", default=5)

    recuperacao_carrinho_ativa = models.BooleanField(
        "Enviar WhatsApp/e-mail pra pedido em andamento esquecido", default=False
    )
    recuperacao_carrinho_horas = models.PositiveIntegerField(
        "Enviar depois de quantas horas em aberto", default=3,
    )
    recuperacao_carrinho_mensagem = models.TextField(
        default="Oi {nome}! Vi que você começou uma compra na Belletti Cards Universe e não finalizou. "
                "Ainda tem interesse? Posso ajudar a fechar! 🎴"
    )

    class Meta:
        verbose_name = "Configuração do CRM"
        verbose_name_plural = "Configuração do CRM"

    def __str__(self):
        return "Configuração do CRM"


def get_config_crm():
    config, _ = ConfiguracaoCRM.objects.get_or_create(pk=1)
    return config
