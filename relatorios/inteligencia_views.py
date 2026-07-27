from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from . import inteligencia as ia
from .views import montar_contexto_dashboard


def gerar_insights(ctx_dashboard, capital_giro_info):
    """
    Gera frases de insight a partir de regras simples sobre os
    números que o sistema já calculou — não é um texto "criativo",
    é template preenchido com dado real, mas já ajuda a enxergar o
    que os números querem dizer sem precisar interpretar tabela.
    """
    insights = []

    comp_mensal = ctx_dashboard.get("comparacao_mensal", {})
    variacao = comp_mensal.get("variacao")
    if variacao is not None:
        if variacao >= 10:
            insights.append(f"📈 Suas vendas estão {variacao:.0f}% acima do mesmo período do mês passado — bom ritmo!")
        elif variacao <= -10:
            insights.append(f"📉 Suas vendas estão {abs(variacao):.0f}% abaixo do mesmo período do mês passado — vale investigar o motivo.")

    ind = ctx_dashboard.get("indicadores", {})
    if ind.get("margem_liquida_pct") is not None:
        if ind["margem_liquida_pct"] < 0:
            insights.append("⚠️ A margem líquida do mês está negativa — as despesas estão maiores que o lucro bruto.")
        elif ind["margem_liquida_pct"] < 10:
            insights.append(f"A margem líquida está em {ind['margem_liquida_pct']:.0f}% — considerada apertada pro varejo, vale revisar preços ou despesas.")

    if capital_giro_info["capital_giro"] < 0:
        insights.append("⚠️ Seu capital de giro está negativo — as obrigações de curto prazo superam o que você tem disponível.")

    if ctx_dashboard.get("qtd_pedidos_andamento", 0) > 0:
        insights.append(f"🛒 Você tem {ctx_dashboard['qtd_pedidos_andamento']} pedido(s) em andamento — pode valer a pena finalizar ou verificar.")

    return insights


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def inteligencia_view(request):
    ctx_dashboard = montar_contexto_dashboard()

    # --- Financeira ------------------------------------------------------------
    previsao_faturamento = ia.prever_proximo_mes(ctx_dashboard.get("valores_mes", []))
    previsao_lucro = ia.prever_proximo_mes(ctx_dashboard.get("valores_lucro", []))
    capital_giro_info = ia.calcular_capital_de_giro()

    sugestoes_preco = []
    for g in ctx_dashboard.get("giro_cobertura", [])[:8]:
        margem, preco = ia.sugerir_margem_e_preco(g["produto"], g["giro"])
        sugestoes_preco.append({
            "produto": g["produto"], "margem_sugerida": margem, "preco_sugerido": preco,
            "preco_atual": g["produto"].preco_venda,
        })

    # --- Estoque -----------------------------------------------------------------
    capital_parado = ia.calcular_capital_parado(ctx_dashboard.get("produtos_parados", []))
    ruptura_iminente = [
        g for g in ctx_dashboard.get("giro_cobertura", [])
        if g["cobertura_dias"] is not None and g["cobertura_dias"] < 15
    ]
    excesso_estoque = [
        g for g in ctx_dashboard.get("giro_cobertura", [])
        if g["cobertura_dias"] is not None and g["cobertura_dias"] > 180
    ]

    # --- Comercial -----------------------------------------------------------------
    inativos = ia.clientes_inativos(dias_inatividade=90)[:10]
    recompra = ia.chance_de_recompra()[:10]
    cesta = ia.produtos_comprados_juntos()

    # --- Gerencial (insights) -------------------------------------------------------
    insights = gerar_insights(ctx_dashboard, capital_giro_info)

    return render(request, "relatorios/inteligencia.html", {
        "previsao_faturamento": previsao_faturamento,
        "previsao_lucro": previsao_lucro,
        "capital_giro_info": capital_giro_info,
        "sugestoes_preco": sugestoes_preco,
        "capital_parado": capital_parado,
        "ruptura_iminente": ruptura_iminente,
        "excesso_estoque": excesso_estoque,
        "clientes_inativos": inativos,
        "chance_recompra": recompra,
        "cesta_de_compras": cesta,
        "insights": insights,
    })
