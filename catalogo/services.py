"""
Serviços de estoque pra produtos compostos (Kit, Combo, Booster Box,
etc). Um produto composto tem seu próprio estoque_atual (é vendido
como unidade fechada normalmente), mas dá pra:

- "Desmontar": abrir N unidades do composto, devolvendo os
  componentes ao estoque individual (ex: abrir uma Booster Box em
  36 Boosters soltos).
- "Montar": consumir os componentes do estoque pra criar N unidades
  do composto (ex: montar um Combo a partir de itens avulsos).
"""
from django.db import transaction


class SemComponentesError(Exception):
    pass


class EstoqueInsuficienteComposicaoError(Exception):
    pass


@transaction.atomic
def abrir_inventario(usuario, categoria=None, observacoes=""):
    from .models import InventarioSessao, ItemInventario, Produto

    if InventarioSessao.objects.filter(fechada_em__isnull=True).exists():
        raise ValueError("Já existe um inventário aberto. Finalize-o antes de abrir outro.")

    produtos_qs = Produto.objects.filter(ativo=True)
    if categoria:
        produtos_qs = produtos_qs.filter(categoria=categoria)

    sessao = InventarioSessao.objects.create(
        aberta_por=usuario, categoria=categoria, observacoes=observacoes
    )
    ItemInventario.objects.bulk_create([
        ItemInventario(sessao=sessao, produto=p, quantidade_esperada=p.estoque_atual)
        for p in produtos_qs
    ])
    return sessao


def registrar_contagem(item_inventario, quantidade_contada):
    from django.utils import timezone
    item_inventario.quantidade_contada = max(quantidade_contada, 0)
    item_inventario.contado_em = timezone.now()
    item_inventario.save(update_fields=["quantidade_contada", "contado_em"])
    return item_inventario


@transaction.atomic
def finalizar_inventario(sessao):
    from django.utils import timezone

    from .models import MovimentacaoEstoque

    if not sessao.aberta:
        raise ValueError("Esse inventário já foi finalizado.")

    ajustados = 0
    for item in sessao.itens.select_related("produto").filter(quantidade_contada__isnull=False):
        diferenca = item.diferenca
        if not diferenca:
            continue
        MovimentacaoEstoque.objects.create(
            produto=item.produto,
            tipo="entrada" if diferenca > 0 else "saida",
            quantidade=abs(diferenca),
            motivo=f"Ajuste de inventário #{sessao.pk}",
        )
        ajustados += 1

    sessao.fechada_em = timezone.now()
    sessao.save(update_fields=["fechada_em"])
    return sessao, ajustados
    from .models import MovimentacaoEstoque

    componentes = list(produto.componentes_kit.select_related("produto_componente"))
    if not componentes:
        raise SemComponentesError(f"{produto.nome} não tem componentes cadastrados.")

    if produto.estoque_atual < quantidade:
        raise EstoqueInsuficienteComposicaoError(
            f"Estoque de {produto.nome} é {produto.estoque_atual}, não dá pra desmontar {quantidade}."
        )

    MovimentacaoEstoque.objects.create(
        produto=produto, tipo="saida", quantidade=quantidade,
        motivo=motivo or f"Desmontagem de {quantidade}x {produto.sku}",
    )
    for comp in componentes:
        MovimentacaoEstoque.objects.create(
            produto=comp.produto_componente, tipo="entrada",
            quantidade=comp.quantidade * quantidade,
            motivo=motivo or f"Desmontagem de {quantidade}x {produto.sku}",
        )


@transaction.atomic
def montar_composto(produto, quantidade, motivo=""):
    from .models import MovimentacaoEstoque

    componentes = list(produto.componentes_kit.select_related("produto_componente"))
    if not componentes:
        raise SemComponentesError(f"{produto.nome} não tem componentes cadastrados.")

    for comp in componentes:
        necessario = comp.quantidade * quantidade
        if comp.produto_componente.estoque_atual < necessario:
            raise EstoqueInsuficienteComposicaoError(
                f"Falta {comp.produto_componente.nome}: precisa de {necessario}, "
                f"tem {comp.produto_componente.estoque_atual}."
            )

    for comp in componentes:
        MovimentacaoEstoque.objects.create(
            produto=comp.produto_componente, tipo="saida",
            quantidade=comp.quantidade * quantidade,
            motivo=motivo or f"Montagem de {quantidade}x {produto.sku}",
        )
    MovimentacaoEstoque.objects.create(
        produto=produto, tipo="entrada", quantidade=quantidade,
        motivo=motivo or f"Montagem de {quantidade}x {produto.sku}",
    )


@transaction.atomic
def gerar_reposicao_automatica():
    """
    Pra cada produto com estoque no mínimo (ou abaixo) que já tem um
    fornecedor padrão definido, gera uma ordem de compra sozinho —
    ou aproveita uma ordem em aberto já existente pra esse
    fornecedor, se houver, em vez de criar uma nova toda vez.
    Não mexe em produtos compostos (esses se resolvem montando a
    partir dos componentes, não comprando prontos).
    """
    from django.db.models import F

    from relatorios.models import get_config_estoque

    from suprimentos.models import ItemOrdemCompra, OrdemCompra

    from .models import Produto

    config = get_config_estoque()
    if not config.reposicao_automatica_ativa:
        return []

    candidatos = Produto.objects.filter(
        ativo=True, tipo_composicao="simples", fornecedor__isnull=False,
        estoque_atual__lte=F("estoque_minimo"),
    ).select_related("fornecedor")

    # produtos que já estão em alguma ordem aberta/parcial — não duplica
    ja_pedidos = set(
        ItemOrdemCompra.objects.filter(
            ordem__status__in=["aberta", "parcial"]
        ).values_list("produto_id", flat=True)
    )

    ordens_geradas = []
    ordens_por_fornecedor = {}

    for produto in candidatos:
        if produto.id in ja_pedidos:
            continue

        if produto.estoque_maximo:
            quantidade_sugerida = max(produto.estoque_maximo - produto.estoque_atual, 1)
        else:
            quantidade_sugerida = max(
                produto.estoque_minimo * config.reposicao_multiplicador_minimo - produto.estoque_atual, 1
            )

        fornecedor_id = produto.fornecedor_id
        if fornecedor_id not in ordens_por_fornecedor:
            ordem = OrdemCompra.objects.create(fornecedor=produto.fornecedor)
            ordens_por_fornecedor[fornecedor_id] = ordem
            ordens_geradas.append(ordem)
        ordem = ordens_por_fornecedor[fornecedor_id]

        ItemOrdemCompra.objects.create(
            ordem=ordem, produto=produto, quantidade=quantidade_sugerida,
            preco_unitario=produto.preco_custo,
        )

    from aprovacoes.services import verificar_aprovacao_compra
    for ordem in ordens_geradas:
        verificar_aprovacao_compra(ordem)

    return ordens_geradas
