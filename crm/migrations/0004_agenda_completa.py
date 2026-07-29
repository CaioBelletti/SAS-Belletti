# Generated for Belletti OS Agenda Completa
from django.db import migrations, models
import django.core.validators


def criar_categorias_padrao(apps, schema_editor):
    Categoria = apps.get_model('crm', 'CategoriaTarefa')
    padroes = [
        ('Financeiro', '#ffb020', 'money', 10),
        ('Eventos e feiras', '#8b6cf2', 'star', 20),
        ('Fornecedores', '#4d9fff', 'truck', 30),
        ('Marketing', '#ff6b8a', 'megaphone', 40),
        ('Pessoal', '#3ecf8e', 'user', 50),
        ('Manutenção', '#e76f51', 'tools', 60),
    ]
    for nome, cor, icone, ordem in padroes:
        Categoria.objects.get_or_create(nome=nome, defaults={'cor': cor, 'icone': icone, 'ordem': ordem, 'ativa': True})

class Migration(migrations.Migration):
    dependencies = [('crm', '0003_categoriatarefa_tarefa_categoria')]
    operations = [
        migrations.AlterField(model_name='categoriatarefa', name='nome', field=models.CharField(max_length=60, unique=True)),
        migrations.AlterField(model_name='categoriatarefa', name='cor', field=models.CharField(default='#8b6cf2', help_text='Cor exibida no calendário.', max_length=7, validators=[django.core.validators.RegexValidator('^#[0-9A-Fa-f]{6}$', 'Informe uma cor hexadecimal válida, como #8b6cf2.')])) ,
        migrations.AddField(model_name='categoriatarefa', name='icone', field=models.CharField(choices=[('calendar','Calendário'),('briefcase','Trabalho'),('money','Financeiro'),('truck','Fornecedor/viagem'),('star','Evento'),('user','Pessoal'),('megaphone','Marketing'),('tools','Manutenção')], default='calendar', max_length=20)),
        migrations.AddField(model_name='categoriatarefa', name='ativa', field=models.BooleanField(default=True)),
        migrations.AddField(model_name='tarefa', name='data_fim', field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name='tarefa', name='dia_inteiro', field=models.BooleanField(default=False)),
        migrations.AddField(model_name='tarefa', name='prioridade', field=models.CharField(choices=[('baixa','Baixa'),('normal','Normal'),('alta','Alta'),('urgente','Urgente')], default='normal', max_length=10)),
        migrations.AddField(model_name='tarefa', name='local', field=models.CharField(blank=True, max_length=180)),
        migrations.AlterField(model_name='tarefa', name='data_vencimento', field=models.DateTimeField(verbose_name='Início')),
        migrations.RunPython(criar_categorias_padrao, migrations.RunPython.noop),
    ]
