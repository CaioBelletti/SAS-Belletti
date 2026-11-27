import os
import uuid
from decimal import Decimal
from cozinha.models import CategoriaPrato, Prato, Mesa

if os.environ.get("BELLETTI_HOMOLOGACAO") != "1":
    raise RuntimeError("Seed permitido somente em homologação")
categoria, _ = CategoriaPrato.objects.get_or_create(nome="Demonstração")
for nome, preco in (("Espetinho de kafta", "12.00"), ("Porção de batatas", "18.00"), ("Suco", "7.00")):
    Prato.objects.get_or_create(nome=nome, descricao="Produto fictício de homologação", defaults={"preco": Decimal(preco), "categoria": categoria})
Mesa.objects.get_or_create(numero=4, defaults={"token_publico": uuid.UUID("bce771d7-610e-4bc9-a9e1-94e43c134004")})

for nome, grupo in (("Espetinho de kafta", "Espetos"), ("Porção de batatas", "Porções"), ("Suco", "Bebidas")):
    categoria_real, _ = CategoriaPrato.objects.get_or_create(nome=grupo)
    Prato.objects.filter(nome=nome, descricao="Produto fictício de homologação").update(categoria=categoria_real)
if not categoria.pratos.exists():
    categoria.delete()

# Conta exclusiva para validação temporária da homologação. Nunca altera conta existente.
from django.contrib.auth import get_user_model
from django.conf import settings
if "cardapio-homologacao-homologacao.up.railway.app" not in settings.ALLOWED_HOSTS:
    raise RuntimeError("Conta de teste permitida somente no host de homologação")
User = get_user_model()
user, created = User.objects.get_or_create(username="teste_rc8", defaults={
    "is_active": True, "is_staff": True, "is_superuser": True,
    "password": "pbkdf2_sha256$1000000$b44bf4e4f0417d2c7a7538e5$bUer84RBXXpkqkEwgAMNuBzXD3+l2aVldUu0MTzvS0w=",
})
print("Conta teste_rc8 criada" if created else "Conta teste_rc8 já existente; não alterada")
