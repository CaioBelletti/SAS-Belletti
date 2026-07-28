from decimal import Decimal

from django.db import transaction


def get_produto_consumo_cozinha():
    """
    Devolve (criando se precisar) o produto placeholder usado só pra
    representar o consumo da cozinha no financeiro — sem precisar
    modelar cada prato como um Produto do catálogo de cartas (que
    tem um monte de campo que não faz sentido pra comida: grading,
    foil, edição...). O estoque desse produto é só um número alto
    fixo, porque aqui quem controla disponibilidade é o campo
    "disponível" do Prato, não estoque de verdade.
    """
    from catalogo.models import Categoria, MovimentacaoEstoque, Produto

    produto = Produto.objects.filter(sku="COZINHA-CONSUMO").first()
    if produto:
        return produto

    categoria, _ = Categoria.objects.get_or_create(nome="Alimentação (cozinha)")
    produto = Produto.objects.create(
        sku="COZINHA-CONSUMO", nome="Consumo — Cardápio da cozinha",
        categoria=categoria, preco_custo=Decimal("0"), preco_venda=Decimal("0"),
        tipo_composicao="simples",
        descricao="Produto interno — representa o valor consumido no cardápio da cozinha. Não vender diretamente no PDV.",
    )
    MovimentacaoEstoque.objects.create(
        produto=produto, tipo="entrada", quantidade=999999, motivo="Estoque simbólico — item de serviço, não físico",
    )
    return produto


@transaction.atomic
def fechar_comanda(comanda, forma_pagamento, usuario, parcelas=1):
    """
    Fecha a comanda de verdade: cria uma Venda no PDV com o valor
    total consumido, processa o pagamento, e linka tudo — assim o
    consumo da cozinha aparece no financeiro/DRE normalmente.
    """
    from vendas.models import ItemVenda, PagamentoVenda, Venda
    from vendas.services import fechar_venda

    if comanda.status != "aberta":
        raise ValueError("Essa comanda já não está mais aberta.")

    valor_total = comanda.valor_total
    if valor_total <= 0:
        raise ValueError("Essa comanda não tem nenhum consumo pra cobrar.")

    produto_consumo = get_produto_consumo_cozinha()

    venda = Venda.objects.create(canal="fisica", vendedor=usuario, forma_pagamento=forma_pagamento)
    ItemVenda.objects.create(
        venda=venda, produto=produto_consumo, quantidade=1, preco_unitario=valor_total,
    )
    PagamentoVenda.objects.create(venda=venda, forma_pagamento=forma_pagamento, valor=valor_total, parcelas=parcelas)

    fechar_venda(venda)

    from django.utils import timezone
    comanda.status = "fechada"
    comanda.venda = venda
    comanda.fechada_por = usuario
    comanda.fechada_em = timezone.now()
    comanda.save(update_fields=["status", "venda", "fechada_por", "fechada_em"])

    return venda
