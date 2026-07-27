"""
Comando pra gerar um backup em arquivo, pensado pra ser agendado
(Agendador de Tarefas do Windows localmente, ou um cron job no Railway).

Uso: python manage.py backup_dados
Salva em backups/backup_AAAAMMDD_HHMMSS.json e mantém só os 10 mais
recentes (apaga os mais antigos automaticamente).
"""
import os
from datetime import datetime

from django.conf import settings
from django.core import management
from django.core.management.base import BaseCommand

APPS_PARA_BACKUP = [
    "catalogo", "vendas", "financeiro", "suprimentos", "relatorios", "auditoria",
]
MANTER_ULTIMOS = 10


class Command(BaseCommand):
    help = "Gera um backup dos dados em backups/ e mantém só os mais recentes."

    def handle(self, *args, **options):
        pasta = settings.BASE_DIR / "backups"
        pasta.mkdir(exist_ok=True)

        nome_arquivo = pasta / f"backup_{datetime.now():%Y%m%d_%H%M%S}.json"
        with open(nome_arquivo, "w", encoding="utf-8") as f:
            management.call_command(
                "dumpdata", *APPS_PARA_BACKUP, indent=2, stdout=f, natural_foreign=True,
            )

        self.stdout.write(self.style.SUCCESS(f"Backup salvo em {nome_arquivo}"))

        backups = sorted(pasta.glob("backup_*.json"), key=os.path.getmtime, reverse=True)
        for antigo in backups[MANTER_ULTIMOS:]:
            antigo.unlink()
            self.stdout.write(f"Removido backup antigo: {antigo.name}")
