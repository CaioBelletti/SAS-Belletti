from django.contrib import admin

from .models import ConfiguracaoNotificacao, InscricaoPush


@admin.register(ConfiguracaoNotificacao)
class ConfiguracaoNotificacaoAdmin(admin.ModelAdmin):
    list_display = ("email_destino", "ativar_email", "whatsapp_numero", "ativar_whatsapp")

    def has_add_permission(self, request):
        # Só uma configuração deve existir (singleton)
        return not ConfiguracaoNotificacao.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(InscricaoPush)
class InscricaoPushAdmin(admin.ModelAdmin):
    list_display = ("usuario", "criada_em")
    readonly_fields = ("endpoint", "p256dh_key", "auth_key", "criada_em")

    def has_add_permission(self, request):
        return False
