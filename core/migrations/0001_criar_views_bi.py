from django.db import migrations

SQL_CRIAR_VIEWS = """
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
    (iv.quantidade * iv.preco_unitario - iv.desconto) AS subtotal_liquido,
    p.preco_custo AS custo_unitario,
    (iv.quantidade * p.preco_custo) AS custo_total_item
FROM vendas_itemvenda iv
JOIN vendas_venda v ON v.id = iv.venda_id
JOIN catalogo_produto p ON p.id = iv.produto_id
LEFT JOIN catalogo_categoria cat ON cat.id = p.categoria_id;

CREATE VIEW vw_bi_estoque AS
SELECT
    p.id AS produto_id,
    p.sku,
    p.nome,
    cat.nome AS categoria_nome,
    p.estoque_atual,
    p.estoque_minimo,
    p.preco_custo,
    p.preco_venda,
    (p.estoque_atual * p.preco_custo) AS valor_estoque_custo,
    (p.estoque_atual * p.preco_venda) AS valor_estoque_venda,
    p.ativo
FROM catalogo_produto p
LEFT JOIN catalogo_categoria cat ON cat.id = p.categoria_id;

CREATE VIEW vw_bi_financeiro AS
SELECT
    'a_pagar' AS tipo,
    cp.id AS conta_id,
    cp.descricao,
    catf.nome AS categoria_nome,
    cp.valor,
    cp.vencimento,
    cp.status,
    cp.fornecedor AS pessoa
FROM financeiro_contapagar cp
LEFT JOIN financeiro_categoriafinanceira catf ON catf.id = cp.categoria_id
UNION ALL
SELECT
    'a_receber' AS tipo,
    cr.id AS conta_id,
    cr.descricao,
    catf.nome AS categoria_nome,
    cr.valor,
    cr.vencimento,
    cr.status,
    cli.nome AS pessoa
FROM financeiro_contareceber cr
LEFT JOIN financeiro_categoriafinanceira catf ON catf.id = cr.categoria_id
LEFT JOIN vendas_cliente cli ON cli.id = cr.cliente_id;
"""

SQL_APAGAR_VIEWS = """
DROP VIEW IF EXISTS vw_bi_vendas;
DROP VIEW IF EXISTS vw_bi_itens_venda;
DROP VIEW IF EXISTS vw_bi_estoque;
DROP VIEW IF EXISTS vw_bi_financeiro;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("catalogo", "0012_produto_preco_maximo_historicopreco"),
        ("vendas", "0013_alter_venda_status"),
        ("financeiro", "0006_configuracaocobranca_and_more"),
    ]

    def _criar_views(apps, schema_editor):
        # As views só fazem sentido (e só são seguras) em PostgreSQL — o
        # SQLite recria tabelas por trás dos panos a cada ALTER TABLE
        # futuro (não suporta ALTER de verdade), o que quebra qualquer
        # view que dependa delas. Em produção (Railway/PostgreSQL),
        # ALTER TABLE é de verdade e a view sobrevive normalmente.
        if schema_editor.connection.vendor != "postgresql":
            return
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(SQL_CRIAR_VIEWS)

    def _apagar_views(apps, schema_editor):
        if schema_editor.connection.vendor != "postgresql":
            return
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(SQL_APAGAR_VIEWS)

    operations = [
        migrations.RunPython(_criar_views, reverse_code=_apagar_views),
    ]
