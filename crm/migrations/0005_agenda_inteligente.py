from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("crm", "0004_agenda_completa")]

    operations = [
        migrations.AddField(
            model_name="tarefa", name="lembrete_minutos",
            field=models.PositiveIntegerField(default=30, help_text="Minutos antes para destacar o compromisso."),
        ),
        migrations.AddField(
            model_name="tarefa", name="origem",
            field=models.CharField(choices=[("manual", "Criado manualmente"), ("financeiro_pagar", "Conta a pagar"), ("financeiro_receber", "Conta a receber"), ("compra", "Ordem de compra"), ("aniversario", "Aniversário de cliente"), ("checklist", "Checklist operacional")], default="manual", editable=False, max_length=24),
        ),
        migrations.AddField(
            model_name="tarefa", name="recorrencia",
            field=models.CharField(choices=[("nenhuma", "Não repetir"), ("diaria", "Diariamente"), ("semanal", "Semanalmente"), ("mensal", "Mensalmente"), ("anual", "Anualmente")], default="nenhuma", max_length=12),
        ),
        migrations.AddField(
            model_name="tarefa", name="referencia_id",
            field=models.PositiveIntegerField(blank=True, editable=False, null=True),
        ),
        migrations.AddField(
            model_name="tarefa", name="referencia_modelo",
            field=models.CharField(blank=True, editable=False, max_length=80),
        ),
        migrations.AddField(
            model_name="tarefa", name="visibilidade",
            field=models.CharField(choices=[("privada", "Somente eu"), ("gestores", "Sócios e gestores"), ("equipe", "Equipe autorizada")], default="gestores", max_length=12),
        ),
        migrations.AddIndex(
            model_name="tarefa",
            index=models.Index(fields=["origem", "referencia_modelo", "referencia_id"], name="crm_tarefa_origem_7bdb34_idx"),
        ),
    ]
