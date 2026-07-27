"""
Campo de modelo Django que fica CRIPTOGRAFADO no banco de dados
(Fernet/AES via a biblioteca `cryptography`), mas se comporta como
um CharField normal em todo o resto do código — a criptografia e
descriptografia acontecem sozinhas, sem precisar mudar nada em
quem usa o campo.

A chave é derivada da SECRET_KEY do projeto (que já é tratada como
segredo/sensível), então não precisa configurar mais nenhuma
variável de ambiente nova.

Dado antigo que já existia no banco ANTES dessa criptografia entrar
(texto puro) continua sendo lido normalmente — só não protegido até
ser salvo de novo (a migração de dados cuida disso automaticamente).
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models


def _get_fernet():
    chave_bruta = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    chave_fernet = base64.urlsafe_b64encode(chave_bruta)
    return Fernet(chave_fernet)


class CampoCriptografado(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 500)  # texto cifrado ocupa mais espaço que o original
        super().__init__(*args, **kwargs)

    def get_prep_value(self, value):
        if not value:
            return value
        return _get_fernet().encrypt(str(value).encode()).decode()

    def from_db_value(self, value, expression, connection):
        if not value:
            return value
        try:
            return _get_fernet().decrypt(value.encode()).decode()
        except (InvalidToken, ValueError):
            # dado salvo antes de existir criptografia — devolve como está
            return value
