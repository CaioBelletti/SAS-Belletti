from django.contrib import admin

from .models import ConfiguracaoEstoque, ConfiguracaoRelatorioAutomatico, MetaMensal, PreferenciaDashboard


@admin.register(ConfiguracaoRelatorioAutomatico)
class ConfiguracaoRelatorioAutomaticoAdmin(admin.ModelAdmin):
    readonly_fields = ("ultimo_envio",)

    def has_add_permission(self, request):
        return not ConfiguracaoRelatorioAutomatico.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PreferenciaDashboard)
class PreferenciaDashboardAdmin(admin.ModelAdmin):
    list_display = ("usuario", "atualizado_em")

    def has_add_permission(self, request):
        return False


@admin.register(ConfiguracaoEstoque)
class ConfiguracaoEstoqueAdmin(admin.ModelAdmin):
    list_display = ("dias_produto_parado",)

    def has_add_permission(self, request):
        return not ConfiguracaoEstoque.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(MetaMensal)
class MetaMensalAdmin(admin.ModelAdmin):
    list_display = ("mes", "valor")
    ordering = ("-mes",)
