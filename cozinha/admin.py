from django.contrib import admin
from django.utils.html import format_html

from .models import (
    AdicionalPrato,
    CategoriaPrato,
    ChamadoAtendente,
    ChecklistItemProducao,
    Comanda,
    EstacaoProducao,
    EtapaPreparo,
    FechamentoComanda,
    HistoricoStatusPedido,
    ItemPedidoAdicional,
    ItemPedidoCozinha,
    Mesa,
    PedidoCozinha,
    Prato,
    ParticipanteMesa, PromocaoCardapio, ItemPromocao, AvaliacaoMesa,
)


@admin.register(CategoriaPrato)
class CategoriaPratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem_exibicao")


@admin.register(EstacaoProducao)
class EstacaoProducaoAdmin(admin.ModelAdmin):
    list_display = ("icone", "nome", "ativa", "ordem")
    list_editable = ("ativa", "ordem")
    search_fields = ("nome",)


class EtapaPreparoInline(admin.TabularInline):
    model = EtapaPreparo
    extra = 1
    fields = ("ordem", "descricao", "obrigatoria")


class AdicionalPratoInline(admin.TabularInline):
    model = AdicionalPrato
    extra = 1
    fields = ("ordem", "nome", "preco_extra", "disponivel")


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "estacao", "preco", "disponivel", "tempo_preparo_min")
    list_filter = ("categoria", "estacao", "disponivel")
    search_fields = ("nome", "descricao", "instrucoes_preparo")
    list_editable = ("disponivel",)
    inlines = [EtapaPreparoInline, AdicionalPratoInline]


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "ativa", "link_qrcode", "link_cardapio")
    list_editable = ("ativa",)
    readonly_fields = ("token_publico",)

    def link_qrcode(self, obj):
        if not obj.pk:
            return "—"
        return format_html('<a href="/cozinha/qrcode/mesa/{}/" target="_blank">🔍 Ver QR code</a>', obj.pk)
    link_qrcode.short_description = "QR code"

    def link_cardapio(self, obj):
        if not obj.pk:
            return "—"
        return format_html(
            '<a href="/cardapio/m/{}/cardapio/" target="_blank">🍽️ Ver cardápio dessa mesa</a>', obj.token_publico
        )
    link_cardapio.short_description = "Cardápio"


class FechamentoComandaInline(admin.TabularInline):
    model = FechamentoComanda
    extra = 0
    readonly_fields = ("venda", "descricao", "valor", "criado_em")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ("mesa", "status", "valor_total_fmt", "aberta_em", "fechada_em")
    list_filter = ("status",)
    readonly_fields = ("aberta_em", "fechada_em", "venda", "fechada_por")
    inlines = [FechamentoComandaInline]

    def valor_total_fmt(self, obj):
        return f"R$ {obj.valor_total:.2f}"
    valor_total_fmt.short_description = "Valor total"


@admin.register(ChamadoAtendente)
class ChamadoAtendenteAdmin(admin.ModelAdmin):
    list_display = ("mesa", "tipo", "atendido", "criado_em")
    list_filter = ("tipo", "atendido")


class ChecklistInline(admin.TabularInline):
    model = ChecklistItemProducao
    extra = 0
    readonly_fields = ("descricao", "ordem", "obrigatoria", "concluido", "concluido_em", "concluido_por")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class ItemPedidoCozinhaInline(admin.TabularInline):
    model = ItemPedidoCozinha
    extra = 0
    readonly_fields = (
        "prato", "quantidade", "preco_unitario", "adicionais_display", "observacao",
        "preparo_concluido", "iniciado_em", "concluido_em",
    )

    def has_add_permission(self, request, obj=None):
        return False

    def adicionais_display(self, obj):
        return ", ".join(a.nome for a in obj.adicionais_escolhidos.all()) or "—"
    adicionais_display.short_description = "Adicionais"


@admin.register(PedidoCozinha)
class PedidoCozinhaAdmin(admin.ModelAdmin):
    list_display = (
        "id", "nome_para_chamar", "mesa_ou_local", "status", "prioridade", "tempo_espera_minutos", "criado_em"
    )
    list_filter = ("status", "prioridade", "itens__prato__estacao")
    readonly_fields = (
        "codigo_acompanhamento", "criado_em", "em_preparo_em", "pronto_em", "entregue_em", "ip", "dispositivo"
    )
    inlines = [ItemPedidoCozinhaInline]


@admin.register(HistoricoStatusPedido)
class HistoricoStatusPedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "status_anterior", "status_novo", "alterado_por", "alterado_em")
    list_filter = ("status_novo", "alterado_em")
    readonly_fields = ("pedido", "status_anterior", "status_novo", "alterado_por", "alterado_em")

    def has_add_permission(self, request):
        return False


class ItemPromocaoInline(admin.TabularInline):
    model = ItemPromocao
    extra = 1

@admin.register(PromocaoCardapio)
class PromocaoCardapioAdmin(admin.ModelAdmin):
    list_display = ("titulo", "preco_promocional", "ativa", "destaque", "inicio", "fim")
    list_filter = ("ativa", "destaque")
    list_editable = ("ativa", "destaque")
    inlines = [ItemPromocaoInline]

@admin.register(ParticipanteMesa)
class ParticipanteMesaAdmin(admin.ModelAdmin):
    list_display = ("nome", "comanda", "total_consumido", "ativo", "entrou_em")
    list_filter = ("ativo", "comanda__mesa")
    search_fields = ("nome",)
    readonly_fields = ("token_dispositivo", "entrou_em")

@admin.register(AvaliacaoMesa)
class AvaliacaoMesaAdmin(admin.ModelAdmin):
    list_display = ("comanda", "participante", "nota_comida", "nota_atendimento", "criado_em")
    list_filter = ("nota_comida", "nota_atendimento", "criado_em")
    search_fields = ("participante__nome", "comentario")
    readonly_fields = ("criado_em",)
