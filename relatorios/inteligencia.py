"""
"IA" com estatística e regras de negócio — sem depender de API
externa nenhuma. Tudo aqui é matemática sobre os dados que o
sistema já tem: médias, tendências, e heurísticas conhecidas de
gestão de estoque/varejo. Não é machine learning, é análise de
dados bem feita.
"""
import statistics
from datetime import timedelta
from decimal import Decimal

from django.db.models import F, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone


# ============================================================
# IA FINANCEIRA
# ============================================================

def prever_proximo_mes(valores_historicos):
    """
    Projeção simples: média dos últimos 3 meses, ajustada pela
    tendência (comparação entre a segunda e a primeira metade do
    histórico recente). Não é IA, é extrapolação de tendência —
    funciona bem com poucos dados, que é o caso normal de um
    negócio pequeno.
    """
    valores = [v for v in valores_historicos if v is not None]
    if len(valores) < 2:
        return None

    ultimos = valores[-3:] if len(valores) >= 3 else valores
    media_recente = statistics.mean(ultimos)

    if len(valores) >= 6:
        primeira_metade = statistics.mean(valores[-6:-3])
        segunda_metade = statistics.mean(valores[-3:])
        tendencia = (segunda_metade - primeira_metade) / primeira_metade if primeira_metade else 0
        tendencia = max(min(tendencia, 0.5), -0.5)  # limita a ±50% pra não disparar com ruído
    else:
        tendencia = 0

    return round(media_recente * (1 + tendencia), 2)


def calcular_capital_de_giro():
    from financeiro.models import CaixaSessao, ContaPagar, ContaReceber
    from catalogo.models import Produto

    hoje = timezone.localdate()
    caixas_abertos = CaixaSessao.objects.filter(fechada_em__isnull=True)
    saldo_caixa = sum((c.saldo_esperado for c in caixas_abertos), Decimal("0"))

    a_receber = ContaReceber.objects.filter(status="pendente").aggregate(t=Sum("valor"))["t"] or Decimal("0")
    a_pagar = ContaPagar.objects.filter(status="pendente").aggregate(t=Sum("valor"))["t"] or Decimal("0")
    valor_estoque = Produto.objects.filter(ativo=True).aggregate(
        t=Sum(F("estoque_atual") * F("preco_custo"))
    )["t"] or Decimal("0")

    ativo_circulante = saldo_caixa + a_receber + valor_estoque
    passivo_circulante = a_pagar
    return {
        "ativo_circulante": ativo_circulante,
        "passivo_circulante": passivo_circulante,
        "capital_giro": ativo_circulante - passivo_circulante,
        "saldo_caixa": saldo_caixa,
        "a_receber": a_receber,
        "valor_estoque": valor_estoque,
        "a_pagar": a_pagar,
    }


def sugerir_margem_e_preco(produto, giro):
    """
    Heurística: produto que gira rápido pode sustentar margem menor
    (compensa no volume); produto parado precisa de margem maior
    (compensa o capital parado e o risco). Margem base de 40%,
    ajustada pra cima ou pra baixo conforme o giro.
    """
    margem_base = Decimal("40")
    if giro is None or giro == 0:
        ajuste = Decimal("15")  # nunca vendeu — margem mais alta, risco maior
    elif giro >= 2:
        ajuste = Decimal("-10")  # gira muito — pode reduzir margem
    elif giro >= 0.5:
        ajuste = Decimal("0")
    else:
        ajuste = Decimal("10")  # gira pouco — margem mais alta

    margem_sugerida = max(margem_base + ajuste, Decimal("10"))
    custo_total = produto.custo_total
    preco_sugerido = (custo_total * (1 + margem_sugerida / 100)).quantize(Decimal("0.01"))
    return margem_sugerida, preco_sugerido


# ============================================================
# IA ESTOQUE
# ============================================================

def calcular_capital_parado(produtos_parados):
    """Soma quanto (em custo) está parado em produtos sem venda recente."""
    total = Decimal("0")
    for item in produtos_parados:
        produto = item["produto"] if isinstance(item, dict) else item.produto
        total += produto.estoque_atual * produto.preco_custo
    return total


def sugerir_compra_inteligente(produto, cobertura_dias, prazo_medio_fornecedor):
    """
    Quantidade sugerida de compra considerando o prazo de entrega do
    fornecedor — a ideia é comprar a tempo de nunca ficar sem
    estoque, mesmo levando em conta o tempo que o fornecedor demora.
    """
    if not prazo_medio_fornecedor or cobertura_dias is None:
        return None
    margem_seguranca_dias = prazo_medio_fornecedor * 1.5
    if cobertura_dias > margem_seguranca_dias:
        return None  # ainda tem tempo de sobra, não precisa comprar agora
    return produto.estoque_minimo * 3


# ============================================================
# IA COMERCIAL
# ============================================================

def clientes_inativos(dias_inatividade=90):
    from vendas.models import Cliente

    hoje = timezone.localdate()
    limite = hoje - timedelta(days=dias_inatividade)
    resultado = []
    for cliente in Cliente.objects.filter(anonimizado=False):
        vendas = cliente.vendas.filter(status="fechada").order_by("-fechada_em")
        ultima = vendas.first()
        if not ultima or ultima.fechada_em.date() > limite:
            continue
        if vendas.count() == 0:
            continue
        resultado.append({
            "cliente": cliente,
            "ultima_compra": ultima.fechada_em.date(),
            "dias_sem_comprar": (hoje - ultima.fechada_em.date()).days,
            "total_gasto": cliente.total_gasto,
        })
    resultado.sort(key=lambda x: -x["total_gasto"])
    return resultado


def chance_de_recompra():
    """
    Pra cada cliente com 2+ compras, calcula o intervalo médio entre
    elas. Se já passou desse intervalo desde a última compra, é
    provavelmente uma boa hora de entrar em contato.
    """
    from vendas.models import Cliente

    hoje = timezone.localdate()
    candidatos = []
    for cliente in Cliente.objects.filter(anonimizado=False):
        datas = list(
            cliente.vendas.filter(status="fechada").order_by("fechada_em").values_list("fechada_em", flat=True)
        )
        if len(datas) < 2:
            continue
        intervalos = [(datas[i + 1] - datas[i]).days for i in range(len(datas) - 1)]
        intervalo_medio = statistics.mean(intervalos)
        dias_desde_ultima = (hoje - datas[-1].date()).days
        if intervalo_medio > 0 and dias_desde_ultima >= intervalo_medio:
            candidatos.append({
                "cliente": cliente,
                "intervalo_medio_dias": round(intervalo_medio),
                "dias_desde_ultima_compra": dias_desde_ultima,
            })
    candidatos.sort(key=lambda x: -(x["dias_desde_ultima_compra"] - x["intervalo_medio_dias"]))
    return candidatos


def produtos_comprados_juntos(limite_produtos=8):
    """
    Análise de cesta de compras simples: quais produtos aparecem
    junto na mesma venda com mais frequência — base pra
    cross-selling ("quem compra X também costuma levar Y").
    """
    from collections import Counter

    from vendas.models import Venda

    hoje = timezone.localdate()
    inicio = hoje - timedelta(days=365)
    vendas = Venda.objects.filter(status="fechada", fechada_em__date__gte=inicio).prefetch_related("itens__produto")

    contagem_pares = Counter()
    nomes = {}
    for venda in vendas:
        produtos_da_venda = list({item.produto_id: item.produto.nome for item in venda.itens.all()}.items())
        nomes.update(dict(produtos_da_venda))
        for i in range(len(produtos_da_venda)):
            for j in range(i + 1, len(produtos_da_venda)):
                par = tuple(sorted([produtos_da_venda[i][0], produtos_da_venda[j][0]]))
                contagem_pares[par] += 1

    mais_comuns = contagem_pares.most_common(limite_produtos)
    return [
        {"produto_a": nomes[a], "produto_b": nomes[b], "vezes_juntos": qtd}
        for (a, b), qtd in mais_comuns if qtd > 1
    ]
