from django.contrib import admin
from django.utils.html import format_html

from .models import (
    CaixaSessao,
    CategoriaFinanceira,
    ConfiguracaoCobranca,
    ContaBancaria,
    ContaPagar,
    ContaReceber,
    ExtratoBancario,
    MovimentoCaixa,
)


@admin.register(ConfiguracaoCobranca)
class ConfiguracaoCobrancaAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracaoCobranca.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ContaBancaria)
class ContaBancariaAdmin(admin.ModelAdmin):
    list_display = ("nome", "banco", "saldo_atual_fmt", "ativa")

    def saldo_atual_fmt(self, obj):
        return f"R$ {obj.saldo_atual:.2f}"
    saldo_atual_fmt.short_description = "Saldo atual"


@admin.register(ExtratoBancario)
class ExtratoBancarioAdmin(admin.ModelAdmin):
    list_display = ("data", "conta_bancaria", "descricao", "valor", "conciliado")
    list_filter = ("conta_bancaria", "conciliado")
    search_fields = ("descricao", "fitid")
    date_hierarchy = "data"


@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo")
    list_filter = ("tipo",)


@admin.register(ContaReceber)
class ContaReceberAdmin(admin.ModelAdmin):
    list_display = ("descricao", "parcela_fmt", "cliente", "valor", "vencimento", "meio_pagamento", "status_com_alerta")
    list_filter = ("status", "categoria", "meio_pagamento")
    search_fields = ("descricao", "numero_boleto", "grupo_parcelamento")
    date_hierarchy = "vencimento"

    def status_com_alerta(self, obj):
        if obj.vencida:
            return format_html('<span style="color:#c0392b;font-weight:bold;">{}</span>', "vencida")
        return obj.get_status_display()
    status_com_alerta.short_description = "Status"

    def parcela_fmt(self, obj):
        if obj.parcela_total > 1:
            return f"{obj.parcela_numero}/{obj.parcela_total}"
        return "—"
    parcela_fmt.short_description = "Parcela"


@admin.register(ContaPagar)
class ContaPagarAdmin(admin.ModelAdmin):
    list_display = ("descricao", "parcela_fmt", "fornecedor", "valor", "vencimento", "meio_pagamento", "status_com_alerta", "recorrente")
    list_filter = ("status", "categoria", "recorrente", "meio_pagamento")
    search_fields = ("descricao", "fornecedor", "numero_boleto", "grupo_parcelamento")
    date_hierarchy = "vencimento"

    def status_com_alerta(self, obj):
        if obj.vencida:
            return format_html('<span style="color:#c0392b;font-weight:bold;">{}</span>', "vencida")
        return obj.get_status_display()
    status_com_alerta.short_description = "Status"

    def parcela_fmt(self, obj):
        if obj.parcela_total > 1:
            return f"{obj.parcela_numero}/{obj.parcela_total}"
        return "—"
    parcela_fmt.short_description = "Parcela"


@admin.register(CaixaSessao)
class CaixaSessaoAdmin(admin.ModelAdmin):
    list_display = ("id", "aberta_por", "aberta_em", "fechada_em", "valor_abertura", "saldo_esperado", "valor_fechamento_informado", "diferenca")
    list_filter = ("aberta_por",)
    readonly_fields = ("aberta_em",)


@admin.register(MovimentoCaixa)
class MovimentoCaixaAdmin(admin.ModelAdmin):
    list_display = ("data", "tipo", "valor", "descricao", "sessao", "conta_bancaria", "conciliado")
    list_filter = ("tipo", "sessao", "conta_bancaria", "conciliado")
    date_hierarchy = "data"
