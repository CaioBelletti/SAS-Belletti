from django.db import models


class RegistroBackup(models.Model):
    """
    Um registro por backup realizado com sucesso — seja pelo botão manual,
    pelo comando agendado local, ou pelo envio por e-mail agendado no
    Railway. Como fica salvo no banco (não no disco), funciona certinho
    mesmo que o backup agendado rode num serviço separado do Railway,
    que não compartilha o mesmo disco/Volume do serviço principal.
    """
    criado_em = models.DateTimeField(auto_now_add=True)
    origem = models.CharField(
        max_length=20,
        choices=[("manual", "Download manual"), ("agendado_local", "Agendado (local)"), ("agendado_email", "Agendado (e-mail)")],
        default="manual",
    )

    class Meta:
        verbose_name = "Registro de backup"
        verbose_name_plural = "Registros de backup"
        ordering = ["-criado_em"]

    def __str__(self):
        return f"Backup em {self.criado_em:%d/%m/%Y %H:%M} ({self.get_origem_display()})"
