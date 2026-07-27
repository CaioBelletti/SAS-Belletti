from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Categoria,
    ComponenteProduto,
    HistoricoPreco,
    InventarioSessao,
    ItemInventario,
    MovimentacaoEstoque,
    Produto,
    Reserva,
    Subcategoria,
    Tag,
)


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nome",)


@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria")
    list_filter = ("categoria",)
    search_fields = ("nome",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("nome",)


class ComponenteProdutoInline(admin.TabularInline):
    model = ComponenteProduto
    fk_name = "produto_pai"
    extra = 1
    autocomplete_fields = ["produto_componente"]
    verbose_name = "Componente (produto que entra nesse composto)"
    verbose_name_plural = "Componentes (só preencha se este for Kit/Combo/Booster Box/etc)"


class HistoricoPrecoInline(admin.TabularInline):
    model = HistoricoPreco
    extra = 0
    fields = ("preco_anterior", "preco_novo", "alterado_em")
    readonly_fields = ("preco_anterior", "preco_novo", "alterado_em")
    can_delete = False
    max_num = 0  # só leitura, nunca criado manualmente aqui

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "sku", "nome", "categoria", "marca", "estado_conservacao", "grading_fmt",
        "preco_venda", "estoque_atual", "alerta_estoque", "ativo",
    )
    list_filter = ("categoria", "subcategoria", "estado_conservacao", "grading_empresa", "foil", "reverse_holo", "promo", "tipo_composicao", "ativo")
    search_fields = (
        "sku", "codigo_interno", "nome", "edicao", "numero_colecao", "codigo_barras", "ean",
        "grading_certificado", "marca", "lote", "numero_serie",
    )
    readonly_fields = ("estoque_atual", "criado_em", "atualizado_em", "preco_sugerido_fmt", "buscar_imagem_link", "preco_medio_venda_fmt")
    filter_horizontal = ("tags",)
    autocomplete_fields = ["categoria", "subcategoria", "fornecedor"]
    inlines = [ComponenteProdutoInline, HistoricoPrecoInline]
    fieldsets = (
        (None, {"fields": ("sku", "codigo_interno", "codigo_barras", "ean", "nome", "marca", "ativo")}),
        ("Classificação", {"fields": ("categoria", "subcategoria", "fornecedor", "tags", "edicao", "numero_colecao", "idioma", "raridade", "foil", "reverse_holo", "promo", "estado_conservacao")}),
        ("Grading / autenticidade", {"fields": ("grading_empresa", "grading_nota", "grading_certificado")}),
        ("Mídia e descrição", {"fields": ("imagem", "buscar_imagem_link", "descricao")}),
        ("Físico", {"fields": ("peso_gramas", "comprimento_cm", "largura_cm", "altura_cm")}),
        ("Preços e custos", {"fields": (
            "preco_custo", "custo_frete", "custo_impostos", "margem_desejada",
            "preco_sugerido_fmt", "preco_venda", "preco_minimo", "preco_maximo", "preco_medio_venda_fmt",
        )}),
        ("Estoque", {"fields": ("estoque_atual", "estoque_minimo", "estoque_maximo", "localizacao", "lote", "validade", "numero_serie")}),
        ("Produto composto", {
            "fields": ("tipo_composicao",),
            "description": "Se este item for montado a partir de outros produtos (Kit, Combo, Booster Box, etc), cadastre os componentes na lista abaixo.",
        }),
        ("Integração", {"fields": ("codigo_olist",)}),
        ("Auditoria", {"fields": ("criado_em", "atualizado_em")}),
    )

    class Media:
        js = ("js/margem_calculo.js",)

    def alerta_estoque(self, obj):
        if obj.estoque_baixo:
            return format_html('<span style="color:#c0392b;font-weight:bold;">{}</span>', "baixo")
        return "ok"
    alerta_estoque.short_description = "Estoque"

    def grading_fmt(self, obj):
        if obj.grading_display:
            return format_html('<span style="color:#8b6cf2;font-weight:bold;">{}</span>', obj.grading_display)
        return "—"
    grading_fmt.short_description = "Grading"

    def preco_sugerido_fmt(self, obj):
        if obj is None or obj.preco_sugerido is None:
            return "— preencha a margem desejada acima —"
        return f"R$ {obj.preco_sugerido} (calculado ao digitar, mas você pode ajustar o preço de venda manualmente)"
    preco_sugerido_fmt.short_description = "Preço sugerido"

    def preco_medio_venda_fmt(self, obj):
        if obj is None or not obj.pk or obj.preco_medio_venda is None:
            return "— sem vendas fechadas ainda —"
        return f"R$ {obj.preco_medio_venda:.2f} (média do que foi vendido de verdade)"
    preco_medio_venda_fmt.short_description = "Preço médio de venda (real)"

    def buscar_imagem_link(self, obj):
        if obj is None or not obj.pk:
            return "Salve o produto primeiro pra poder buscar a imagem."
        tem_jogo = obj.categoria and obj.categoria.jogo_tcg
        tem_codigo = obj.ean or obj.codigo_barras
        if not tem_jogo and not tem_codigo:
            return (
                "Sem jogo configurado na categoria e sem código de barras/EAN cadastrado — "
                "preencha um dos dois pra habilitar a busca automática."
            )
        url = f"/catalogo/produto/{obj.pk}/buscar-imagem/"
        if tem_jogo:
            texto = f"🔍 Buscar imagem automaticamente ({obj.categoria.get_jogo_tcg_display()} ou código de barras)"
        else:
            texto = "🔍 Buscar imagem automaticamente (por código de barras)"
        return format_html('<a href="{}" style="color:#8b6cf2; font-weight:600;" target="_blank">{}</a>', url, texto)
    buscar_imagem_link.short_description = "Imagem automática"


class ItemInventarioInline(admin.TabularInline):
    model = ItemInventario
    extra = 0
    fields = ("produto", "quantidade_esperada", "quantidade_contada", "contado_em")
    readonly_fields = ("produto", "quantidade_esperada", "contado_em")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(InventarioSessao)
class InventarioSessaoAdmin(admin.ModelAdmin):
    list_display = ("id", "aberta_por", "categoria", "aberta_em", "fechada_em", "total_itens", "total_divergentes")
    list_filter = ("categoria",)
    readonly_fields = ("aberta_em",)
    inlines = [ItemInventarioInline]


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ("produto", "cliente", "quantidade", "status", "validade", "criada_em")
    list_filter = ("status",)
    search_fields = ("produto__nome", "produto__sku")
    autocomplete_fields = ["produto", "cliente"]


@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ("produto", "tipo", "quantidade", "motivo", "venda", "criado_em")
    list_filter = ("tipo",)
    search_fields = ("produto__sku", "produto__nome", "motivo")
    date_hierarchy = "criado_em"
