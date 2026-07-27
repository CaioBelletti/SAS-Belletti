from decimal import Decimal

from django.db import transaction
from django.utils import timezone


class OrdemJaRecebidaError(Exception):
    pass


class NadaRecebidoError(Exception):
    pass


@transaction.atomic
def conferir_recebimento(ordem, recebimentos):
    """
    Registra um evento de recebimento (pode ser parcial). `recebimentos`
    é um dict {item_id: quantidade_recebida_agora}. Dá entrada no
    estoque só da quantidade informada, lança uma conta a pagar
    referente a esse recebimento, e atualiza o status da ordem:
    - "recebida" se todos os itens completaram a quantidade pedida
    - "parcial" se ainda falta alguma coisa (fica em backorder)
    """
    from catalogo.models import MovimentacaoEstoque
    from financeiro.models import CategoriaFinanceira, ContaPagar

    if ordem.status not in ("aberta", "parcial"):
        raise OrdemJaRecebidaError("Essa ordem de compra já foi totalmente recebida ou está cancelada.")

    itens_por_id = {item.id: item for item in ordem.itens.select_related("produto")}
    if not itens_por_id:
        raise ValueError("Não é possível receber uma ordem sem itens.")

    valor_evento = Decimal("0")
    algo_recebido = False

    for item_id, qtd_str in recebimentos.items():
        try:
            qtd_agora = int(qtd_str)
        except (TypeError, ValueError):
            continue
        if qtd_agora <= 0:
            continue
        item = itens_por_id.get(int(item_id))
        if not item:
            continue

        MovimentacaoEstoque.objects.create(
            produto=item.produto,
            tipo="entrada",
            quantidade=qtd_agora,
            motivo=f"Recebimento ordem de compra #{ordem.pk} — {ordem.fornecedor.nome}",
        )
        item.quantidade_recebida = item.quantidade_recebida + qtd_agora
        item.save(update_fields=["quantidade_recebida"])
        valor_evento += qtd_agora * item.preco_unitario
        algo_recebido = True

    if not algo_recebido:
        raise NadaRecebidoError("Nenhuma quantidade recebida foi informada.")

    categoria_compras, _ = CategoriaFinanceira.objects.get_or_create(
        nome="Compra de estoque", tipo="despesa"
    )
    ContaPagar.objects.create(
        descricao=f"Recebimento ordem de compra #{ordem.pk}",
        fornecedor=ordem.fornecedor.nome,
        categoria=categoria_compras,
        valor=valor_evento,
        vencimento=timezone.localdate(),
    )

    itens_atualizados = list(ordem.itens.all())
    tudo_completo = all(i.quantidade_recebida >= i.quantidade for i in itens_atualizados)
    ordem.status = "recebida" if tudo_completo else "parcial"
    if tudo_completo:
        ordem.recebida_em = timezone.now()
    ordem.save(update_fields=["status", "recebida_em"])

    return ordem


def receber_ordem_compra(ordem):
    """
    Atalho pro fluxo antigo: recebe tudo de uma vez, exatamente como
    foi pedido (sem conferência item a item). Usado pela ação rápida
    do admin — internamente já usa a mesma lógica de conferência.
    """
    if ordem.status not in ("aberta", "parcial"):
        raise OrdemJaRecebidaError("Essa ordem de compra já foi totalmente recebida ou está cancelada.")

    recebimentos = {
        str(item.id): item.pendente for item in ordem.itens.all() if item.pendente > 0
    }
    if not recebimentos:
        raise NadaRecebidoError("Não há nada pendente de recebimento nessa ordem.")
    return conferir_recebimento(ordem, recebimentos)
