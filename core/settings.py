"""
Configurações do projeto Belletti Cards Universe — PDV.

Local: usa SQLite automaticamente (nenhuma configuração extra).
Railway: defina a variável de ambiente DATABASE_URL (o Railway já
cria isso sozinho quando você adiciona um serviço PostgreSQL) e
SECRET_KEY. O sistema detecta e troca para PostgreSQL sozinho.
"""

from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config(
    "SECRET_KEY",
    default="django-insecure-troque-esta-chave-em-producao",
)

DEBUG = config("DEBUG", default=True, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv()
)
if DEBUG:
    # Em desenvolvimento local, libera acesso de qualquer dispositivo na
    # mesma rede (ex: celular testando o PDV) — nunca em produção, já
    # que lá DEBUG=False e isso não se aplica.
    ALLOWED_HOSTS.append("*")
# O Railway expõe o domínio público nesta variável — já liberamos automaticamente.
RAILWAY_DOMAIN = config("RAILWAY_PUBLIC_DOMAIN", default="")
if RAILWAY_DOMAIN:
    ALLOWED_HOSTS.append(RAILWAY_DOMAIN)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS", default="", cast=Csv()
)
if RAILWAY_DOMAIN:
    CSRF_TRUSTED_ORIGINS.append(f"https://{RAILWAY_DOMAIN}")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "catalogo",
    "vendas",
    "financeiro",
    "relatorios",
    "suprimentos",
    "auditoria",
    "notificacoes",
    "crm",
    "aprovacoes",
    "cozinha",
    "seguranca",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "seguranca.middleware.RateLimitEIPBloqueadoMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "seguranca.middleware.ControleDeAreaMiddleware",
    "seguranca.middleware.AtualizarSessaoAtivaMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Banco de dados: SQLite local por padrão, PostgreSQL se DATABASE_URL existir
# (é isso que o Railway injeta automaticamente).
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# Imagens de produto. ATENÇÃO: no Railway, o disco é temporário — se
# você fizer redeploy, as imagens enviadas aqui se perdem. Pra guardar
# de verdade em produção, o ideal é usar um serviço externo (Cloudinary,
# S3, etc). Localmente funciona sem problema nenhum.
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# E-mail: por padrão só imprime no console (bom pra testar localmente
# sem precisar configurar nada). Pra mandar e-mails de verdade, defina
# EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD no ambiente
# (funciona com Gmail, SendGrid, etc — veja o README).
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_BACKEND = config(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.smtp.EmailBackend" if EMAIL_HOST
    else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="belletti@localhost")

# Prints de tela em alta resolução podem passar do limite padrão (2.5MB).
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# @login_required manda pra cá quando o usuário não está logado —
# tela de login própria, que funciona pra qualquer usuário ativo
# (vendedor não-staff incluso), diferente do /admin/login/ que exige
# is_staff=True.
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/relatorios/"
