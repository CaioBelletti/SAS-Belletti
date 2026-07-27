import io
import os
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import user_passes_test
from django.core import management
from django.http import HttpResponse

APPS_PARA_BACKUP = [
    "catalogo", "vendas", "financeiro", "suprimentos", "relatorios", "auditoria",
]
MANTER_ULTIMOS = 10


def _salvar_copia_local(conteudo):
    """Salva uma cópia em backups/, igual o comando agendado faz — assim
    tanto o backup manual quanto o automático contam pro 'último backup'."""
    pasta = settings.BASE_DIR / "backups"
    pasta.mkdir(exist_ok=True)
    nome_arquivo = pasta / f"backup_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write(conteudo)

    backups = sorted(pasta.glob("backup_*.json"), key=os.path.getmtime, reverse=True)
    for antigo in backups[MANTER_ULTIMOS:]:
        antigo.unlink()


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def baixar_backup(request):
    buffer = io.StringIO()
    management.call_command(
        "dumpdata", *APPS_PARA_BACKUP, indent=2, stdout=buffer, natural_foreign=True,
    )
    conteudo = buffer.getvalue()

    try:
        _salvar_copia_local(conteudo)
    except OSError:
        pass  # não deixa a falha de salvar local impedir o download

    nome_arquivo = f"backup_belletti_{datetime.now():%Y%m%d_%H%M%S}.json"
    response = HttpResponse(conteudo, content_type="application/json")
    response["Content-Disposition"] = f'attachment; filename="{nome_arquivo}"'
    return response


def dias_desde_ultimo_backup():
    """Devolve quantos dias faz desde o backup mais recente, ou None se nunca teve nenhum."""
    pasta = settings.BASE_DIR / "backups"
    if not pasta.exists():
        return None
    backups = sorted(pasta.glob("backup_*.json"), key=os.path.getmtime, reverse=True)
    if not backups:
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(backups[0]))
    return (datetime.now() - mtime).days
