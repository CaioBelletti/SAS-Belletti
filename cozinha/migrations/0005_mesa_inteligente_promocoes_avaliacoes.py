import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [('cozinha','0004_pedido_em_entrega')]
    operations = [
        migrations.CreateModel(
            name='ParticipanteMesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=80)),
                ('token_dispositivo', models.UUIDField(db_index=True, default=uuid.uuid4)),
                ('entrou_em', models.DateTimeField(auto_now_add=True)),
                ('ativo', models.BooleanField(default=True)),
                ('comanda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participantes', to='cozinha.comanda')),
            ],
            options={'verbose_name':'Jogador/cliente da mesa','verbose_name_plural':'Jogadores/clientes da mesa'},
        ),
        migrations.AddConstraint(model_name='participantemesa', constraint=models.UniqueConstraint(fields=('comanda','token_dispositivo'), name='uniq_participante_dispositivo_comanda')),
        migrations.AddField(
            model_name='pedidocozinha', name='participante',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pedidos', to='cozinha.participantemesa'),
        ),
        migrations.CreateModel(
            name='PromocaoCardapio',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=120)),
                ('descricao', models.CharField(blank=True, max_length=240)),
                ('preco_promocional', models.DecimalField(decimal_places=2, max_digits=8, validators=[django.core.validators.MinValueValidator(0)])),
                ('imagem', models.ImageField(blank=True, upload_to='promocoes/%Y/%m/')),
                ('ativa', models.BooleanField(default=True)),
                ('destaque', models.BooleanField(default=True)),
                ('inicio', models.DateTimeField(blank=True, null=True)),
                ('fim', models.DateTimeField(blank=True, null=True)),
                ('ordem', models.PositiveIntegerField(default=0)),
            ],
            options={'verbose_name':'Promoção do cardápio','verbose_name_plural':'Promoções do cardápio','ordering':['ordem','titulo']},
        ),
        migrations.CreateModel(
            name='ItemPromocao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantidade', models.PositiveIntegerField(default=1)),
                ('prato', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='cozinha.prato')),
                ('promocao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='cozinha.promocaocardapio')),
            ],
            options={'verbose_name':'Item da promoção','verbose_name_plural':'Itens da promoção'},
        ),
        migrations.CreateModel(
            name='AvaliacaoMesa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota_comida', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('nota_atendimento', models.PositiveSmallIntegerField(validators=[django.core.validators.MinValueValidator(1)])),
                ('comentario', models.CharField(blank=True, max_length=500)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('comanda', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='avaliacoes', to='cozinha.comanda')),
                ('participante', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='avaliacoes', to='cozinha.participantemesa')),
                ('pedido', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='avaliacoes', to='cozinha.pedidocozinha')),
            ],
            options={'verbose_name':'Avaliação da mesa','verbose_name_plural':'Avaliações das mesas','ordering':['-criado_em']},
        ),
    ]
