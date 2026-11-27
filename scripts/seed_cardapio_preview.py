"""Run with python manage.py shell < scripts/seed_cardapio_preview.py."""
import os
from decimal import Decimal
from django.db import transaction
from cozinha.models import CategoriaPrato, Prato

if os.environ.get("CARDAPIO_DEMO_SEED") != "preview-only":
    raise RuntimeError("Demo seed disabled")
if os.environ.get("RAILWAY_SERVICE_NAME") != "cardapio-v2-preview":
    raise RuntimeError("Not the preview service")

with transaction.atomic():
    if Prato.objects.exists() or CategoriaPrato.objects.exists():
        raise RuntimeError("Catalog is not empty; refusing to modify it")
    for ordem, (categoria, itens) in enumerate([
        ("Espetos — DEMO", [("Espetinho de kafta", "12.00")]),
        ("Porções — DEMO", [("Porção de fritas", "25.00")]),
        ("Bebidas — DEMO", [("Refrigerante", "7.00")]),
        ("Sobremesas — DEMO", [("Torta doce", "15.00")]),
    ]):
        cat = CategoriaPrato.objects.create(nome=categoria, ordem_exibicao=ordem)
        for nome, preco in itens:
            Prato.objects.create(nome=nome + " — DEMO", descricao="Produto demonstrativo; não disponível para compra real.", preco=Decimal(preco), categoria=cat, disponivel=True)
print("Demo catalog created")
