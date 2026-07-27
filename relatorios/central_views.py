import statistics
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone

from catalogo.models import Categoria, Produto
from vendas.models import Cliente, Devolucao, ItemDevolucao, ItemVenda, PerfilVendedor, Venda


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def central_relatorios(request):
    hoje = timezone.localdate()
    inicio_periodo = hoje.replace(day=1) - timedelta(days=365)
    vendas_periodo = Venda.objects.filter(status="fechada", fechada_em__date__gte=inicio_periodo)

    # --- Relatório por categoria --------------------------------------------------
    itens_periodo = ItemVenda.objects.filter(venda__in=vendas_periodo)
    categorias_dados = (
        itens_periodo.values("produto__categoria__nome")
        .annotate(
            quantidade_total=Sum("quantidade"),
            receita=Sum(F("quantidade") * F("preco_unitario")),
            cmv=Sum(F("quantidade") * F("produto__preco_custo")),
        )
        .order_by("-receita")
    )
    receita_total_categorias = sum((c["receita"] or Decimal("0")) for c in categorias_dados) or Decimal("1")
    relatorio_categorias = []
    for c in categorias_dados:
        receita = c["receita"] or Decimal("0")
        cmv = c["cmv"] or Decimal("0")
        relatorio_categorias.append({
            "nome": c["produto__categoria__nome"] or "Sem categoria",
            "quantidade": c["quantidade_total"],
            "receita": receita,
            "margem": receita - cmv,
            "percentual": round((receita / receita_total_categorias) * 100, 1),
        })

    # --- Relatório de clientes ------------------------------------------------------
    clientes_dados = []
    for cliente in Cliente.objects.filter(anonimizado=False):
        vendas_cliente = vendas_periodo.filter(cliente=cliente)
        total = sum((v.total for v in vendas_cliente), Decimal("0"))
        qtd = vendas_cliente.count()
        if qtd == 0:
            continue
        clientes_dados.append({
            "nome": cliente.nome, "total_gasto": total, "numero_compras": qtd,
            "ticket_medio": (total / qtd).quantize(Decimal("0.01")),
        })
    clientes_dados.sort(key=lambda x: x["total_gasto"], reverse=True)
    relatorio_clientes = clientes_dados[:15]

    # --- Análise XYZ (previsibilidade de demanda) -----------------------------------
    vendas_mensais_produto = (
        itens_periodo
        .annotate(mes=TruncMonth("venda__fechada_em"))
        .values("produto__nome", "produto__sku", "mes")
        .annotate(qtd=Sum("quantidade"))
    )
    por_produto = {}
    for linha in vendas_mensais_produto:
        chave = (linha["produto__nome"], linha["produto__sku"])
        por_produto.setdefault(chave, []).append(linha["qtd"])

    relatorio_xyz = []
    for (nome, sku), valores in por_produto.items():
        if len(valores) < 2:
            classe = "Z"
            cv = None
        else:
            media = statistics.mean(valores)
            desvio = statistics.stdev(valores)
            cv = round(desvio / media, 2) if media else None
            if cv is None:
                classe = "Z"
            elif cv <= 0.5:
                classe = "X"
            elif cv <= 1.0:
                classe = "Y"
            else:
                classe = "Z"
        relatorio_xyz.append({
            "nome": nome, "sku": sku, "cv": cv, "classe": classe,
            "meses_com_venda": len(valores), "total_vendido": sum(valores),
        })
    relatorio_xyz.sort(key=lambda x: (x["classe"], -x["total_vendido"]))

    # --- Relatório de devoluções -----------------------------------------------------
    devolucoes_periodo = Devolucao.objects.filter(processada=True, processada_em__date__gte=inicio_periodo)
    total_devolucoes = devolucoes_periodo.count()
    valor_devolvido = ItemDevolucao.objects.filter(
        devolucao__in=devolucoes_periodo
    ).aggregate(total=Sum(F("quantidade") * F("preco_unitario")))["total"] or Decimal("0")

    motivos_devolucao = (
        devolucoes_periodo.exclude(motivo="").values("motivo")
        .annotate(qtd=Count("id")).order_by("-qtd")[:10]
    )

    devolucoes_por_mes = (
        devolucoes_periodo.annotate(mes=TruncMonth("processada_em"))
        .values("mes").annotate(qtd=Count("id")).order_by("mes")
    )

    # --- Desempenho de funcionários --------------------------------------------------
    vendedores_dados = (
        vendas_periodo.filter(vendedor__isnull=False)
        .values("vendedor__username")
        .annotate(
            total_vendido=Sum(F("itens__quantidade") * F("itens__preco_unitario")),
            numero_vendas=Count("id", distinct=True),
            itens_vendidos=Sum("itens__quantidade"),
        )
        .order_by("-total_vendido")
    )
    relatorio_funcionarios = []
    for v in vendedores_dados:
        total = v["total_vendido"] or Decimal("0")
        numero = v["numero_vendas"] or 0
        relatorio_funcionarios.append({
            "vendedor": v["vendedor__username"],
            "total_vendido": total,
            "numero_vendas": numero,
            "itens_vendidos": v["itens_vendidos"] or 0,
            "ticket_medio": (total / numero).quantize(Decimal("0.01")) if numero else Decimal("0"),
        })

    return render(request, "relatorios/central.html", {
        "relatorio_categorias": relatorio_categorias,
        "relatorio_clientes": relatorio_clientes,
        "relatorio_xyz": relatorio_xyz,
        "total_devolucoes": total_devolucoes,
        "valor_devolvido": valor_devolvido,
        "motivos_devolucao": motivos_devolucao,
        "devolucoes_por_mes": list(devolucoes_por_mes),
        "relatorio_funcionarios": relatorio_funcionarios,
    })
