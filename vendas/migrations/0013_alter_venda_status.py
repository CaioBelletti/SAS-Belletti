from django.db import migrations, models


SQL_REMOVER_VIEWS = """
DROP VIEW IF EXISTS vw_bi_vendas;
DROP VIEW IF EXISTS vw_bi_itens_venda;
"""


SQL_RECRIAR_VIEWS = """
CREATE VIEW vw_bi_vendas AS
SELECT
    v.id AS venda_id,
    v.fechada_em AS data_fechamento,
    v.canal,
    v.status,
    v.desconto,
    v.acrescimo,
    c.nome AS cliente_nome,
    c.cidade AS cliente_cidade,
    c.uf AS cliente_uf,
    u.username AS vendedor
FROM vendas_venda v
LEFT JOIN vendas_cliente c ON c.id = v.cliente_id
LEFT JOIN auth_user u ON u.id = v.vendedor_id;


CREATE VIEW vw_bi_itens_venda AS
SELECT
    iv.id AS item_id,
    v.id AS venda_id,
    v.fechada_em AS data_fechamento,
    v.status AS status_venda,
    p.sku AS produto_sku,
    p.nome AS produto_nome,
    cat.nome AS categoria_nome,
    iv.quantidade,
    iv.preco_unitario,
    iv.desconto AS desconto_item,
    (
        iv.quantidade * iv.preco_unitario - iv.desconto
    ) AS subtotal_liquido,
    p.preco_custo AS custo_unitario,
    (
        iv.quantidade * p.preco_custo
    ) AS custo_total_item
FROM vendas_itemvenda iv
JOIN vendas_venda v
    ON v.id = iv.venda_id
JOIN catalogo_produto p
    ON p.id = iv.produto_id
LEFT JOIN catalogo_categoria cat
    ON cat.id = p.categoria_id;
"""


def remover_views(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_REMOVER_VIEWS)


def recriar_views(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(SQL_RECRIAR_VIEWS)


class Migration(migrations.Migration):

    dependencies = [
        ("vendas", "0012_vendaofflinependente_venda_uuid_offline"),
    ]

    operations = [
        migrations.RunPython(
            remover_views,
            reverse_code=migrations.RunPython.noop,
        ),

        migrations.AlterField(
            model_name="venda",
            name="status",
            field=models.CharField(
                choices=[
                    ("orcamento", "Orçamento"),
                    ("aberta", "Aberta"),
                    (
                        "pendente_aprovacao",
                        "Aguardando aprovação de desconto",
                    ),
                    ("fechada", "Fechada"),
                    ("cancelada", "Cancelada"),
                ],
                default="aberta",
                max_length=20,
            ),
        ),

        migrations.RunPython(
            recriar_views,
            reverse_code=remover_views,
        ),
    ]
