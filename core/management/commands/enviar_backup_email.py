"""
Comando pensado especificamente pro Cron Job do Railway — como um
serviço de cron ali roda separado do serviço principal (sem
compartilhar o mesmo disco/Volume), a forma confiável de "guardar"
o backup é mandando ele por e-mail, em vez de salvar em arquivo local.

Uso: python manage.py enviar_backup_email
"""
import io
from datetime import datetime

from django.core import management
from django.core.mail import EmailMessage
from django.core.management.base import BaseCommand, CommandError

APPS_PARA_BACKUP = [
    "catalogo", "vendas", "financeiro", "suprimentos", "relatorios", "auditoria",
]


class Command(BaseCommand):
    help = "Gera o backup e manda por e-mail pro endereço configurado (pensado pro Cron Job do Railway)."

    def handle(self, *args, **options):
        from notificacoes.models import get_config

        config = get_config()
        if not config.email_destino:
            raise CommandError(
                "Nenhum e-mail de destino configurado (Admin → Notificações → "
                "Configuração de notificações). Configure antes de agendar isso."
            )

        buffer = io.StringIO()
        management.call_command(
            "dumpdata", *APPS_PARA_BACKUP, indent=2, stdout=buffer, natural_foreign=True,
        )
        conteudo = buffer.getvalue()
        nome_arquivo = f"backup_belletti_{datetime.now():%Y%m%d_%H%M%S}.json"

        email = EmailMessage(
            subject=f"Backup automático — Belletti Cards Universe ({datetime.now():%d/%m/%Y})",
            body=(
                "Segue em anexo o backup automático dos dados do sistema.\n\n"
                "Guarde esse e-mail — em caso de problema no sistema, esse arquivo "
                "pode ser restaurado com o comando 'loaddata'."
            ),
            to=[config.email_destino],
        )
        email.attach(nome_arquivo, conteudo, "application/json")
        email.send(fail_silently=False)

        from core.models import RegistroBackup
        RegistroBackup.objects.create(origem="agendado_email")

        self.stdout.write(self.style.SUCCESS(f"Backup enviado por e-mail pra {config.email_destino}"))
