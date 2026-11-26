from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("cozinha", "0006_adicionalprato_fechamentocomanda_itempedidoadicional")]
    operations = [
        migrations.CreateModel(
            name="RequisicaoPedido",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chave", models.UUIDField(unique=True)),
                ("assinatura", models.CharField(max_length=64)),
                ("resposta", models.JSONField(default=dict)),
                ("criado_em", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
