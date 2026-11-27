#!/bin/sh
# Executar em ambiente isolado com configuração equivalente à produção.
# Não executa migrate nem popula dados.
set -eu
python - <<'PY'
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
import django
django.setup()
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
errors = []
if settings.DEBUG: errors.append("DEBUG deve ser False")
if not settings.SECRET_KEY or len(settings.SECRET_KEY) < 50: errors.append("SECRET_KEY inadequada")
if not settings.ALLOWED_HOSTS or "*" in settings.ALLOWED_HOSTS: errors.append("ALLOWED_HOSTS inadequado")
if not settings.CSRF_TRUSTED_ORIGINS or any(not x.startswith("https://") for x in settings.CSRF_TRUSTED_ORIGINS): errors.append("CSRF_TRUSTED_ORIGINS inadequado")
if settings.DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql": errors.append("PostgreSQL obrigatório")
if errors: raise ImproperlyConfigured("; ".join(errors))
print("Configuração básica aprovada")
PY
python manage.py check --deploy --fail-level WARNING
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
echo "Verificações concluídas. Backup restaurado, revisão do plano e aprovação humana ainda são obrigatórios."
