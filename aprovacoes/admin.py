from django.contrib import admin

from .models import NivelAprovacao, RegistroDecisao, RegraAprovacao, SolicitacaoAprovacao


class NivelAprovacaoInline(admin.TabularInline):
    model = NivelAprovacao
    extra = 1


@admin.register(RegraAprovacao)
class RegraAprovacaoAdmin(admin.ModelAdmin):
    list_display = ("tipo", "ativa", "valor_limite")
    inlines = [NivelAprovacaoInline]


class RegistroDecisaoInline(admin.TabularInline):
    model = RegistroDecisao
    extra = 0
    readonly_fields = ("nivel", "aprovador", "decisao", "comentario", "decidido_em")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(SolicitacaoAprovacao)
class SolicitacaoAprovacaoAdmin(admin.ModelAdmin):
    list_display = ("descricao", "tipo", "valor", "nivel_atual", "status", "solicitado_por", "criada_em")
    list_filter = ("tipo", "status")
    readonly_fields = ("content_type", "object_id", "tipo", "descricao", "valor", "solicitado_por", "criada_em")
    inlines = [RegistroDecisaoInline]

    def has_add_permission(self, request):
        return False
