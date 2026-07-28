# Generated for Belletti OS — Cozinha 2.0

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def criar_estacoes_padrao(apps, schema_editor):
    Estacao = apps.get_model("cozinha", "EstacaoProducao")
    Prato = apps.get_model("cozinha", "Prato")
    padroes = [
        ("Cozinha", "🍔", "#ef4444", 10),
        ("Bar", "🥤", "#3b82f6", 20),
        ("Cafeteria", "☕", "#a16207", 30),
        ("Doces", "🧁", "#ec4899", 40),
        ("Expedição", "📦", "#22c55e", 50),
    ]
    estacoes = {}
    for nome, icone, cor, ordem in padroes:
        estacoes[nome], _ = Estacao.objects.get_or_create(
            nome=nome, defaults={"icone": icone, "cor": cor, "ordem": ordem}
        )

    for prato in Prato.objects.select_related("categoria").all():
        categoria = (prato.categoria.nome if prato.categoria else "").lower()
        nome = prato.nome.lower()
        texto = f"{categoria} {nome}"
        destino = "Cozinha"
        if any(p in texto for p in ["refrigerante", "bebida", "suco", "água", "agua", "energético", "energetico"]):
            destino = "Bar"
        elif any(p in texto for p in ["café", "cafe", "capuccino", "espresso", "chá", "cha"]):
            destino = "Cafeteria"
        elif any(p in texto for p in ["doce", "sobremesa", "brownie", "bolo", "cookie"]):
            destino = "Doces"
        prato.estacao = estacoes[destino]
        prato.save(update_fields=["estacao"])


def remover_estacoes_padrao(apps, schema_editor):
    Estacao = apps.get_model("cozinha", "EstacaoProducao")
    Estacao.objects.filter(nome__in=["Cozinha", "Bar", "Cafeteria", "Doces", "Expedição"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("cozinha", "0002_mesa_pedidocozinha_dispositivo_pedidocozinha_ip_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="EstacaoProducao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nome", models.CharField(max_length=60, unique=True)),
                ("icone", models.CharField(blank=True, default="🍳", max_length=12)),
                ("cor", models.CharField(default="#7c3aed", help_text="Cor hexadecimal, ex.: #7c3aed", max_length=7)),
                ("ativa", models.BooleanField(default=True)),
                ("ordem", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Estação de produção",
                "verbose_name_plural": "Estações de produção",
                "ordering": ["ordem", "nome"],
            },
        ),
        migrations.AddField(
            model_name="prato",
            name="instrucoes_preparo",
            field=models.TextField(blank=True, help_text="Ex.: grelhar hambúrguer, aquecer pão, montar e embalar.", verbose_name="Instruções rápidas de preparo"),
        ),
        migrations.AddField(
            model_name="prato",
            name="estacao",
            field=models.ForeignKey(blank=True, help_text="Estação responsável por preparar este item.", null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pratos", to="cozinha.estacaoproducao"),
        ),
        migrations.CreateModel(
            name="EtapaPreparo",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descricao", models.CharField(max_length=180)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("obrigatoria", models.BooleanField(default=True)),
                ("prato", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="etapas_preparo", to="cozinha.prato")),
            ],
            options={
                "verbose_name": "Etapa de preparo",
                "verbose_name_plural": "Etapas de preparo",
                "ordering": ["ordem", "id"],
            },
        ),
        migrations.AddField(
            model_name="itempedidocozinha",
            name="preparo_concluido",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="itempedidocozinha",
            name="iniciado_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="itempedidocozinha",
            name="concluido_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="ChecklistItemProducao",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("descricao", models.CharField(max_length=180)),
                ("ordem", models.PositiveIntegerField(default=0)),
                ("obrigatoria", models.BooleanField(default=True)),
                ("concluido", models.BooleanField(default=False)),
                ("concluido_em", models.DateTimeField(blank=True, null=True)),
                ("concluido_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("item_pedido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checklist", to="cozinha.itempedidocozinha")),
            ],
            options={
                "verbose_name": "Item do checklist de produção",
                "verbose_name_plural": "Checklist de produção",
                "ordering": ["ordem", "id"],
            },
        ),
        migrations.CreateModel(
            name="HistoricoStatusPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status_anterior", models.CharField(blank=True, max_length=12)),
                ("status_novo", models.CharField(max_length=12)),
                ("alterado_em", models.DateTimeField(auto_now_add=True)),
                ("alterado_por", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ("pedido", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="historico_status", to="cozinha.pedidocozinha")),
            ],
            options={
                "verbose_name": "Histórico de status do pedido",
                "verbose_name_plural": "Históricos de status dos pedidos",
                "ordering": ["-alterado_em"],
            },
        ),
        migrations.RunPython(criar_estacoes_padrao, remover_estacoes_padrao),
    ]
