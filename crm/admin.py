from django.contrib import admin

from .models import ConfiguracaoCRM, InteracaoContato, Lead, Proposta, Tarefa


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
    list_display = ("titulo", "responsavel", "data_vencimento", "concluida", "gerada_automaticamente")
    list_filter = ("concluida", "gerada_automaticamente", "responsavel")
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
