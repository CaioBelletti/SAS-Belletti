"""
Verifica se já existe algum usuário administrador cadastrado.
Sai com código 0 se existir, 1 se não existir — usado pelo iniciar.bat
para decidir se precisa pedir pra você criar um.
"""
import os
import sys
from pathlib import Path

import django

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth import get_user_model  # noqa: E402

existe = get_user_model().objects.filter(is_superuser=True).exists()
sys.exit(0 if existe else 1)
