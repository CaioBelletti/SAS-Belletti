from django.contrib import admin
from django.contrib.auth.models import Group

from .models import Area, DoisFatores, IPBloqueado, PerfilAcesso, SessaoAtiva, TentativaLogin


@admin.register(DoisFatores)
class DoisFatoresAdmin(admin.ModelAdmin):
    list_display = ("usuario", "ativado", "criado_em")
    readonly_fields = ("secret", "criado_em")

    def has_add_permission(self, request):
        return False


@admin.register(TentativaLogin)
class TentativaLoginAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "username", "sucesso", "ip")
    list_filter = ("sucesso",)
    search_fields = ("username", "ip")
    date_hierarchy = "criado_em"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nome", "codigo")
    search_fields = ("nome", "codigo")


@admin.register(IPBloqueado)
class IPBloqueadoAdmin(admin.ModelAdmin):
    list_display = ("ip", "motivo", "criado_em")
    search_fields = ("ip",)


@admin.register(SessaoAtiva)
class SessaoAtivaAdmin(admin.ModelAdmin):
    list_display = ("usuario", "ip", "dispositivo", "criada_em", "ultima_atividade")
    list_filter = ("usuario",)
    readonly_fields = ("session_key", "criada_em", "ultima_atividade")

    def has_add_permission(self, request):
        return False


class PerfilAcessoInline(admin.StackedInline):
    model = PerfilAcesso
    filter_horizontal = ("areas",)
    can_delete = False


class GroupAdminComPerfil(admin.ModelAdmin):
    inlines = [PerfilAcessoInline]
    list_display = ("name",)
    search_fields = ("name",)


# Substitui o admin padrão de Grupo (Django) pelo nosso, que já
# inclui o controle de áreas junto — assim dá pra editar tudo numa
# tela só (Admin → Autenticação e autorização → Grupos).
admin.site.unregister(Group)
admin.site.register(Group, GroupAdminComPerfil)
