from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("cozinha", "0003_cozinha_2_0"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedidocozinha",
            name="em_entrega_em",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="pedidocozinha",
            name="status",
            field=models.CharField(
                choices=[
                    ("recebido", "Recebido"),
                    ("em_preparo", "Em preparo"),
                    ("pronto", "Pronto"),
                    ("em_entrega", "Em entrega"),
                    ("entregue", "Entregue"),
                    ("cancelado", "Cancelado"),
                ],
                default="recebido",
                max_length=12,
            ),
        ),
    ]
