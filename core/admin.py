from django.contrib import admin

from .models import RegistroBackup


@admin.register(RegistroBackup)
class RegistroBackupAdmin(admin.ModelAdmin):
    list_display = ("criado_em", "origem")
    list_filter = ("origem",)
    readonly_fields = ("criado_em", "origem")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
