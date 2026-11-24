from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [("seguranca", "0003_ipbloqueado")]
    operations = [
        migrations.AddField(model_name="doisfatores", name="ultimo_totp", field=models.BigIntegerField(default=-1)),
        migrations.CreateModel(name="CodigoRecuperacao", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("digest", models.CharField(max_length=256)),
            ("usado_em", models.DateTimeField(null=True, blank=True)),
            ("config", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="codigos_recuperacao", to="seguranca.doisfatores")),
        ]),
    ]
