from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CategoriaPrato, ChamadoAtendente, Comanda, ItemPedidoCozinha, Mesa, PedidoCozinha, Prato,
)


@admin.register(CategoriaPrato)
class CategoriaPratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem_exibicao")


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "disponivel", "tempo_preparo_min")
    list_filter = ("categoria", "disponivel")
    search_fields = ("nome", "descricao")
    list_editable = ("disponivel",)


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ("numero", "nome", "ativa", "link_qrcode")
    list_editable = ("ativa",)
    readonly_fields = ("token_publico",)

    def link_qrcode(self, obj):
        if not obj.pk:
            return "—"
        return format_html(
            '<a href="/cozinha/qrcode/mesa/{}/" target="_blank">🔍 Ver QR code</a>', obj.pk
        )
    link_qrcode.short_description = "QR code"


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ("mesa", "status", "valor_total_fmt", "aberta_em", "fechada_em")
    list_filter = ("status",)
    readonly_fields = ("aberta_em", "fechada_em", "venda", "fechada_por")

    def valor_total_fmt(self, obj):
        return f"R$ {obj.valor_total:.2f}"
    valor_total_fmt.short_description = "Valor total"


@admin.register(ChamadoAtendente)
class ChamadoAtendenteAdmin(admin.ModelAdmin):
    list_display = ("mesa", "tipo", "atendido", "criado_em")
    list_filter = ("tipo", "atendido")


class ItemPedidoCozinhaInline(admin.TabularInline):
    model = ItemPedidoCozinha
    extra = 0
    readonly_fields = ("prato", "quantidade", "preco_unitario", "observacao")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(PedidoCozinha)
class PedidoCozinhaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome_para_chamar", "mesa_ou_local", "status", "prioridade", "criado_em")
    list_filter = ("status", "prioridade")
    readonly_fields = ("codigo_acompanhamento", "criado_em", "ip", "dispositivo")
    inlines = [ItemPedidoCozinhaInline]
