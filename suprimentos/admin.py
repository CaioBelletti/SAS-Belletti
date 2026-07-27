from django.contrib import admin, messages

from .models import Cotacao, Fornecedor, ItemCotacao, ItemOrdemCompra, OrdemCompra, PropostaCotacao
from .services import NadaRecebidoError, OrdemJaRecebidaError, receber_ordem_compra


@admin.register(Fornecedor)
class FornecedorAdmin(admin.ModelAdmin):
    list_display = ("nome", "documento", "telefone", "avaliacao_fmt")
    list_filter = ("avaliacao",)
    search_fields = ("nome", "documento")

    def avaliacao_fmt(self, obj):
        if not obj.avaliacao:
            return "—"
        return "★" * obj.avaliacao + "☆" * (5 - obj.avaliacao)
    avaliacao_fmt.short_description = "Avaliação"


class ItemOrdemCompraInline(admin.TabularInline):
    model = ItemOrdemCompra
    extra = 1
    autocomplete_fields = ["produto"]
    readonly_fields = ("quantidade_recebida",)


@admin.register(OrdemCompra)
class OrdemCompraAdmin(admin.ModelAdmin):
    list_display = ("id", "fornecedor", "status", "total", "backorder_fmt", "data_prevista", "criada_em")
    list_filter = ("status", "fornecedor")
    inlines = [ItemOrdemCompraInline]
    readonly_fields = ("criada_em", "recebida_em")
    actions = ["acao_receber_ordem"]

    def backorder_fmt(self, obj):
        return "sim" if obj.tem_backorder else "—"
    backorder_fmt.short_description = "Backorder"

    @admin.action(description="Receber tudo que falta (dá entrada no estoque e lança conta a pagar)")
    def acao_receber_ordem(self, request, queryset):
        from auditoria.models import registrar
        for ordem in queryset:
            try:
                receber_ordem_compra(ordem)
                registrar(request.user, "ordem_recebida", f"Ordem #{ordem.pk} — {ordem.fornecedor.nome} — R$ {ordem.total}", request=request)
                self.message_user(request, f"Ordem #{ordem.pk}: recebimento registrado.", messages.SUCCESS)
            except (OrdemJaRecebidaError, NadaRecebidoError, ValueError) as exc:
                self.message_user(request, f"Ordem #{ordem.pk}: {exc}", messages.ERROR)


class ItemCotacaoInline(admin.TabularInline):
    model = ItemCotacao
    extra = 1
    autocomplete_fields = ["produto"]


@admin.register(Cotacao)
class CotacaoAdmin(admin.ModelAdmin):
    list_display = ("id", "status", "criada_em")
    list_filter = ("status",)
    inlines = [ItemCotacaoInline]


@admin.register(PropostaCotacao)
class PropostaCotacaoAdmin(admin.ModelAdmin):
    list_display = ("item_cotacao", "fornecedor", "preco_unitario", "prazo_dias")
    list_filter = ("fornecedor",)
    autocomplete_fields = ["fornecedor"]
