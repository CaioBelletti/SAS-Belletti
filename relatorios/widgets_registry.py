"""
Registro central dos widgets do dashboard. A ordem aqui é a ordem
PADRÃO — usada pra quem nunca personalizou nada, e também define
quais IDs são válidos (proteção contra dado velho/malicioso vindo
da preferência salva do usuário).
"""

WIDGETS_PADRAO = [
    ("central_alertas", "Central de alertas", "relatorios/widgets/central_alertas.html"),
    ("pedidos_andamento", "Pedidos em andamento", "relatorios/widgets/pedidos_andamento.html"),
    ("meta_reestoque", "Meta do mês e reestoque", "relatorios/widgets/meta_reestoque.html"),
    ("produtos_parados", "Produtos parados", "relatorios/widgets/produtos_parados.html"),
    ("quick_panel", "Resumo rápido", "relatorios/widgets/quick_panel.html"),
    ("comparacoes", "Comparação mensal e anual", "relatorios/widgets/comparacoes.html"),
    ("indicadores", "Indicadores financeiros", "relatorios/widgets/indicadores.html"),
    ("fluxo_completo", "Fluxo de caixa completo", "relatorios/widgets/fluxo_completo.html"),
    ("aniversariantes", "Aniversariantes do mês", "relatorios/widgets/aniversariantes.html"),
    ("vendas_mes", "Gráfico de vendas por mês", "relatorios/widgets/vendas_mes.html"),
    ("lucro_mes", "Gráfico de lucro por mês", "relatorios/widgets/lucro_mes.html"),
    ("receita_dia_semana", "Receita diária e semanal", "relatorios/widgets/receita_dia_semana.html"),
    ("comissao_abc", "Comissão e curva ABC", "relatorios/widgets/comissao_abc.html"),
    ("fluxo_vencimentos", "Fluxo de caixa e vencimentos", "relatorios/widgets/fluxo_vencimentos.html"),
    ("dre", "DRE simplificado", "relatorios/widgets/dre.html"),
    ("produtos_mais_horarios", "Produtos mais vendidos e horários", "relatorios/widgets/produtos_mais_horarios.html"),
    ("produtos_menos_vendidos", "Produtos menos vendidos", "relatorios/widgets/produtos_menos_vendidos.html"),
    ("giro_cobertura", "Giro e cobertura de estoque", "relatorios/widgets/giro_cobertura.html"),
    ("heatmap", "Heatmap de vendas", "relatorios/widgets/heatmap.html"),
]

WIDGETS_POR_ID = {w[0]: {"label": w[1], "template": w[2]} for w in WIDGETS_PADRAO}
IDS_PADRAO = [w[0] for w in WIDGETS_PADRAO]


def montar_lista_widgets(preferencia):
    """
    Combina a ordem salva do usuário (se existir) com os widgets
    padrão, protegendo contra IDs inválidos/antigos e incluindo
    automaticamente widgets novos que o usuário ainda não conhece
    (aparecem no final, visíveis por padrão).
    """
    ordem_salva = []
    ocultos = set()

    if preferencia:
        ordem_salva = [wid for wid in (preferencia.ordem_widgets or []) if wid in WIDGETS_POR_ID]
        ocultos = set(wid for wid in (preferencia.widgets_ocultos or []) if wid in WIDGETS_POR_ID)

    # começa pela ordem salva, depois anexa qualquer widget novo que
    # ainda não estava na lista do usuário (ex: lançamos um widget novo)
    ordem_final = list(ordem_salva)
    for wid in IDS_PADRAO:
        if wid not in ordem_final:
            ordem_final.append(wid)

    widgets = []
    for wid in ordem_final:
        info = WIDGETS_POR_ID[wid]
        widgets.append({
            "id": wid,
            "label": info["label"],
            "template": info["template"],
            "oculto": wid in ocultos,
        })
    return widgets
