from django.contrib import admin

from .models import CategoriaTarefa, ConfiguracaoCRM, InteracaoContato, Lead, Proposta, Tarefa


@admin.register(CategoriaTarefa)
class CategoriaTarefaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cor_preview", "icone", "ativa", "ordem")
    list_editable = ("ativa", "ordem")
    list_filter = ("ativa", "icone")
    search_fields = ("nome",)

    def cor_preview(self, obj):
        from django.utils.html import format_html
        return format_html(
            '<span style="display:inline-block;width:14px;height:14px;border-radius:4px;background:{};margin-right:6px;vertical-align:middle;"></span>{}',
            obj.cor, obj.cor,
        )
    cor_preview.short_description = "Cor"


class InteracaoContatoInline(admin.TabularInline):
    model = InteracaoContato
    extra = 0
    fields = ("tipo", "descricao", "criada_por", "criada_em")
    readonly_fields = ("criada_em",)


class TarefaInline(admin.TabularInline):
    model = Tarefa
    extra = 0
    fields = ("titulo", "responsavel", "data_vencimento", "concluida")


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("nome", "etapa", "origem", "valor_estimado", "responsavel", "dias_sem_interacao_fmt")
    list_filter = ("etapa", "origem")
    search_fields = ("nome", "telefone", "email")
    autocomplete_fields = ["cliente"]
    inlines = [InteracaoContatoInline, TarefaInline]

    def dias_sem_interacao_fmt(self, obj):
        return f"{obj.dias_sem_interacao} dia(s)"
    dias_sem_interacao_fmt.short_description = "Sem interação há"


@admin.register(InteracaoContato)
class InteracaoContatoAdmin(admin.ModelAdmin):
    list_display = ("criada_em", "tipo", "lead", "cliente", "criada_por")
    list_filter = ("tipo",)
    search_fields = ("descricao",)
    autocomplete_fields = ["lead", "cliente"]


@admin.register(Tarefa)
class TarefaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "prioridade", "responsavel", "data_vencimento", "data_fim", "concluida", "gerada_automaticamente")
    list_filter = ("concluida", "categoria", "prioridade", "dia_inteiro", "gerada_automaticamente", "responsavel")
    search_fields = ("titulo", "descricao")
    autocomplete_fields = ["lead", "cliente"]


@admin.register(Proposta)
class PropostaAdmin(admin.ModelAdmin):
    list_display = ("titulo", "lead", "cliente", "valor", "validade", "status")
    list_filter = ("status",)
    search_fields = ("titulo",)
    autocomplete_fields = ["lead", "cliente"]


@admin.register(ConfiguracaoCRM)
class ConfiguracaoCRMAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return not ConfiguracaoCRM.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
