from django.contrib import admin

from .models import CategoriaPrato, ItemPedidoCozinha, PedidoCozinha, Prato


@admin.register(CategoriaPrato)
class CategoriaPratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem_exibicao")


@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "preco", "disponivel", "tempo_preparo_min")
    list_filter = ("categoria", "disponivel")
    search_fields = ("nome", "descricao")
    list_editable = ("disponivel",)


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
    readonly_fields = ("codigo_acompanhamento", "criado_em")
    inlines = [ItemPedidoCozinhaInline]
