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


def _gerar_venda_parcial(valor, forma_pagamento, usuario, parcelas=1):
    """Cria uma Venda de verdade no PDV pra um valor específico (uma parte ou o total)."""
    from vendas.models import ItemVenda, PagamentoVenda, Venda
    from vendas.services import fechar_venda

    produto_consumo = get_produto_consumo_cozinha()
    venda = Venda.objects.create(canal="fisica", vendedor=usuario, forma_pagamento=forma_pagamento)
    ItemVenda.objects.create(venda=venda, produto=produto_consumo, quantidade=1, preco_unitario=valor)
    PagamentoVenda.objects.create(venda=venda, forma_pagamento=forma_pagamento, valor=valor, parcelas=parcelas)
    fechar_venda(venda)
    return venda


@transaction.atomic
def fechar_comanda(comanda, forma_pagamento, usuario, parcelas=1):
    """
    Fecha a comanda de verdade (tudo junto, sem dividir): cria uma
    Venda no PDV com o valor total consumido, processa o pagamento,
    e linka tudo — assim o consumo da cozinha aparece no
    financeiro/DRE normalmente.
    """
    from django.utils import timezone

    from .models import FechamentoComanda

    if comanda.status != "aberta":
        raise ValueError("Essa comanda já não está mais aberta.")

    valor_total = comanda.valor_total
    if valor_total <= 0:
        raise ValueError("Essa comanda não tem nenhum consumo pra cobrar.")

    venda = _gerar_venda_parcial(valor_total, forma_pagamento, usuario, parcelas)
    FechamentoComanda.objects.create(comanda=comanda, venda=venda, descricao="Fechamento único", valor=valor_total)

    comanda.status = "fechada"
    comanda.venda = venda
    comanda.fechada_por = usuario
    comanda.fechada_em = timezone.now()
    comanda.save(update_fields=["status", "venda", "fechada_por", "fechada_em"])

    return venda


class DivisaoInvalidaError(ValueError):
    pass


@transaction.atomic
def fechar_comanda_dividida(comanda, divisoes, usuario):
    """
    Fecha a comanda dividindo em várias partes — cada uma vira uma
    Venda própria no PDV. `divisoes` é uma lista de dicts:
    [{"descricao": "...", "valor": Decimal, "forma_pagamento": "..."}]
    A soma das partes precisa bater com o total da comanda (com uma
    tolerância mínima de 1 centavo pra arredondamento).
    """
    from django.utils import timezone

    from .models import FechamentoComanda

    if comanda.status != "aberta":
        raise ValueError("Essa comanda já não está mais aberta.")

    if not divisoes:
        raise DivisaoInvalidaError("Informe pelo menos uma parte pra dividir a conta.")

    valor_total = comanda.valor_total
    if valor_total <= 0:
        raise ValueError("Essa comanda não tem nenhum consumo pra cobrar.")

    soma_partes = sum((Decimal(str(d["valor"])) for d in divisoes), Decimal("0"))
    if abs(soma_partes - valor_total) > Decimal("0.01"):
        raise DivisaoInvalidaError(
            f"A soma das partes (R$ {soma_partes:.2f}) não bate com o total da comanda (R$ {valor_total:.2f})."
        )

    vendas_geradas = []
    for divisao in divisoes:
        valor_parte = Decimal(str(divisao["valor"]))
        if valor_parte <= 0:
            continue
        venda = _gerar_venda_parcial(valor_parte, divisao["forma_pagamento"], usuario)
        FechamentoComanda.objects.create(
            comanda=comanda, venda=venda, descricao=divisao.get("descricao", ""), valor=valor_parte,
        )
        vendas_geradas.append(venda)

    comanda.status = "fechada"
    comanda.venda = vendas_geradas[-1] if vendas_geradas else None
    comanda.fechada_por = usuario
    comanda.fechada_em = timezone.now()
    comanda.save(update_fields=["status", "venda", "fechada_por", "fechada_em"])

    return vendas_geradas
