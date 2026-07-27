from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    Cliente,
    ConfiguracaoFidelidade,
    CupomDesconto,
    Devolucao,
    ItemDevolucao,
    ItemVenda,
    PagamentoVenda,
    PerfilVendedor,
    Vale,
    Venda,
    VendaOfflinePendente,
)
from .services import (
    DevolucaoJaProcessadaError,
    EstoqueInsuficienteError,
    QuantidadeDevolucaoInvalidaError,
    VendaJaFechadaError,
    fechar_venda,
    processar_devolucao,
)


@admin.register(ConfiguracaoFidelidade)
class ConfiguracaoFidelidadeAdmin(admin.ModelAdmin):
    list_display = ("ativo", "valor_por_ponto", "valor_resgate_ponto", "percentual_cashback")

    def has_add_permission(self, request):
        return not ConfiguracaoFidelidade.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CupomDesconto)
class CupomDescontoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "tipo", "valor", "ativo", "validade", "usos_atuais", "usos_maximos")
    list_filter = ("tipo", "ativo")
    search_fields = ("codigo",)
    readonly_fields = ("usos_atuais",)


@admin.register(Vale)
class ValeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "valor_inicial", "saldo", "ativo", "criado_em")
    list_filter = ("ativo",)
    search_fields = ("codigo",)
    readonly_fields = ("criado_em",)


@admin.register(PerfilVendedor)
class PerfilVendedorAdmin(admin.ModelAdmin):
    list_display = ("usuario", "percentual_comissao")
    autocomplete_fields = []


class VendaHistoricoInline(admin.TabularInline):
    """Histórico de compras do cliente — só leitura, dentro da própria ficha dele."""
    model = Venda
    extra = 0
    fields = ("id", "status", "canal", "total", "fechada_em")
    readonly_fields = ("id", "status", "canal", "total", "fechada_em")
    can_delete = False
    verbose_name_plural = "Histórico de compras"

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    class Media:
        js = ("js/cep-autofill.js",)

    list_display = (
        "nome", "telefone", "email", "blacklist_fmt", "pontos_fidelidade",
        "saldo_credito", "total_gasto_fmt", "numero_compras",
    )
    list_filter = ("blacklist", "consentimento_dados", "anonimizado")
    search_fields = ("nome", "documento", "email", "telefone")
    readonly_fields = (
        "pontos_fidelidade", "valor_pontos_em_reais", "saldo_credito",
        "total_gasto", "numero_compras", "anonimizado",
    )
    fieldsets = (
        (None, {"fields": ("nome", "telefone", "email", "documento", "data_nascimento")}),
        ("Endereço", {"fields": ("cep", "logradouro", "numero", "complemento", "bairro", "cidade", "uf")}),
        ("Fidelidade", {"fields": ("pontos_fidelidade", "valor_pontos_em_reais", "saldo_credito")}),
        ("LGPD", {"fields": ("consentimento_dados", "consentimento_em", "anonimizado")}),
        ("Restrição", {"fields": ("blacklist", "blacklist_motivo")}),
        ("Histórico", {"fields": ("total_gasto", "numero_compras")}),
    )
    inlines = [VendaHistoricoInline]
    actions = ["acao_anonimizar"]

    def total_gasto_fmt(self, obj):
        return f"R$ {obj.total_gasto:.2f}"
    total_gasto_fmt.short_description = "Total gasto"

    def blacklist_fmt(self, obj):
        if obj.blacklist:
            return format_html('<span style="color:#f26d6d;font-weight:bold;">{}</span>', "restrito")
        return "—"
    blacklist_fmt.short_description = "Blacklist"

    @admin.action(description="Anonimizar dados pessoais (direito ao esquecimento — LGPD)")
    def acao_anonimizar(self, request, queryset):
        from .services import anonimizar_cliente
        for cliente in queryset:
            anonimizar_cliente(cliente)
        self.message_user(request, f"{queryset.count()} cliente(s) anonimizado(s).", messages.SUCCESS)


class ItemVendaInline(admin.TabularInline):
    model = ItemVenda
    extra = 1
    autocomplete_fields = ["produto"]


class PagamentoVendaInline(admin.TabularInline):
    model = PagamentoVenda
    extra = 0
    fields = ("forma_pagamento", "valor", "parcelas", "vale")


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "vendedor", "canal", "status", "forma_pagamento", "total", "aberta_em")
    list_filter = ("status", "forma_pagamento", "canal")
    search_fields = ("id",)
    inlines = [ItemVendaInline, PagamentoVendaInline]
    readonly_fields = ("aberta_em", "fechada_em")
    actions = ["acao_fechar_venda", "acao_converter_orcamento"]

    @admin.action(description="Fechar venda selecionada (baixa estoque e lança financeiro)")
    def acao_fechar_venda(self, request, queryset):
        from auditoria.models import registrar
        for venda in queryset:
            try:
                fechar_venda(venda)
                registrar(request.user, "venda_fechada", f"Venda #{venda.pk} fechada pelo admin", request=request)
                self.message_user(request, f"Venda #{venda.pk} fechada.", messages.SUCCESS)
            except (VendaJaFechadaError, EstoqueInsuficienteError, ValueError) as exc:
                self.message_user(request, f"Venda #{venda.pk}: {exc}", messages.ERROR)

    @admin.action(description="Converter orçamento em venda aberta (pra depois fechar)")
    def acao_converter_orcamento(self, request, queryset):
        convertidos = 0
        for venda in queryset:
            if venda.status != "orcamento":
                self.message_user(request, f"Venda #{venda.pk} não é um orçamento.", messages.WARNING)
                continue
            venda.status = "aberta"
            venda.save(update_fields=["status"])
            convertidos += 1
        if convertidos:
            self.message_user(request, f"{convertidos} orçamento(s) convertido(s) em venda aberta.", messages.SUCCESS)


class ItemDevolucaoInline(admin.TabularInline):
    model = ItemDevolucao
    extra = 1
    autocomplete_fields = ["produto"]


@admin.register(Devolucao)
class DevolucaoAdmin(admin.ModelAdmin):
    list_display = ("id", "venda", "total", "processada", "criada_em")
    list_filter = ("processada",)
    inlines = [ItemDevolucaoInline]
    readonly_fields = ("criada_em", "processada_em")
    autocomplete_fields = ["venda"]
    actions = ["acao_processar_devolucao"]

    @admin.action(description="Processar devolução (devolve estoque e estorna no financeiro)")
    def acao_processar_devolucao(self, request, queryset):
        from auditoria.models import registrar
        for devolucao in queryset:
            try:
                processar_devolucao(devolucao)
                registrar(request.user, "devolucao_processada", f"Devolução #{devolucao.pk} — venda #{devolucao.venda_id}", request=request)
                self.message_user(request, f"Devolução #{devolucao.pk} processada.", messages.SUCCESS)
            except (DevolucaoJaProcessadaError, QuantidadeDevolucaoInvalidaError, ValueError) as exc:
                self.message_user(request, f"Devolução #{devolucao.pk}: {exc}", messages.ERROR)


@admin.register(VendaOfflinePendente)
class VendaOfflinePendenteAdmin(admin.ModelAdmin):
    list_display = ("uuid_offline", "erro", "resolvida", "criada_em")
    list_filter = ("resolvida",)
    readonly_fields = ("uuid_offline", "payload_json", "erro", "criada_em")
    actions = ["marcar_como_resolvida"]

    @admin.action(description="Marcar como resolvida (depois de tratar manualmente)")
    def marcar_como_resolvida(self, request, queryset):
        atualizadas = queryset.update(resolvida=True)
        self.message_user(request, f"{atualizadas} registro(s) marcado(s) como resolvido(s).")
