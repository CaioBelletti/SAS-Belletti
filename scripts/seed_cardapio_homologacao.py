import os
import uuid
from decimal import Decimal
from cozinha.models import CategoriaPrato, Prato, Mesa

if os.environ.get("BELLETTI_HOMOLOGACAO") != "1":
    raise RuntimeError("Seed permitido somente em homologação")
categoria, _ = CategoriaPrato.objects.get_or_create(nome="Demonstração")
for nome, preco in (("Espetinho de kafta", "12.00"), ("Porção de batatas", "18.00"), ("Suco", "7.00")):
    Prato.objects.get_or_create(nome=nome, categoria=categoria, defaults={"preco": Decimal(preco), "descricao": "Produto fictício de homologação"})
Mesa.objects.get_or_create(numero=4, defaults={"token_publico": uuid.UUID("bce771d7-610e-4bc9-a9e1-94e43c134004")})

for nome, grupo in (("Espetinho de kafta", "Espetos"), ("Porção de batatas", "Porções"), ("Suco", "Bebidas")):
    categoria_real, _ = CategoriaPrato.objects.get_or_create(nome=grupo)
    Prato.objects.filter(nome=nome, descricao="Produto fictício de homologação").update(categoria=categoria_real)
if not categoria.pratos.exists():
    categoria.delete()
