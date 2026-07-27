import csv
import json
from datetime import timedelta
from io import BytesIO

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Count, F, Sum
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone


COORDENADAS_UF = {
    "AC": (-9.0238, -70.812), "AL": (-9.5713, -36.782), "AP": (1.4144, -51.7865),
    "AM": (-3.4168, -65.8561), "BA": (-12.5797, -41.7007), "CE": (-5.4984, -39.3206),
    "DF": (-15.7998, -47.8645), "ES": (-19.1834, -40.3089), "GO": (-15.827, -49.8362),
    "MA": (-4.9609, -45.2744), "MT": (-12.6819, -56.9211), "MS": (-20.7722, -54.7852),
    "MG": (-18.5122, -44.555), "PA": (-3.9014, -52.4791), "PB": (-7.2399, -36.782),
    "PR": (-25.2521, -52.0215), "PE": (-8.8137, -36.9541), "PI": (-8.5619, -42.9), "PT": (-8.5619, -42.9),
    "RJ": (-22.9068, -43.1729), "RN": (-5.7945, -36.782), "RS": (-30.0346, -51.2177),
    "RO": (-11.5057, -63.5806), "RR": (2.7376, -62.0751), "SC": (-27.2423, -50.2189),
    "SP": (-23.5505, -46.6333), "SE": (-10.5741, -37.3857), "TO": (-10.1753, -48.2982),
}


def _clientes_por_estado():
    from vendas.models import Cliente

    dados = (
        Cliente.objects.filter(anonimizado=False)
        .exclude(uf="")
        .values("uf")
        .annotate(total=Count("id"))
    )
    resultado = []
    for item in dados:
        coords = COORDENADAS_UF.get(item["uf"].upper())
        if coords:
            resultado.append({"uf": item["uf"].upper(), "total": item["total"], "lat": coords[0], "lng": coords[1]})
    return resultado


def _aplicar_filtros(request):
    from vendas.models import ItemVenda

    hoje = timezone.localdate()
    data_inicio = request.GET.get("data_inicio") or (hoje - timedelta(days=30)).isoformat()
    data_fim = request.GET.get("data_fim") or hoje.isoformat()
    categoria_id = request.GET.get("categoria") or ""
    vendedor_id = request.GET.get("vendedor") or ""

    itens = ItemVenda.objects.filter(
        venda__status="fechada",
        venda__fechada_em__date__gte=data_inicio,
        venda__fechada_em__date__lte=data_fim,
    ).select_related("venda", "venda__cliente", "venda__vendedor", "produto", "produto__categoria")

    if categoria_id:
        itens = itens.filter(produto__categoria_id=categoria_id)
    if vendedor_id:
        itens = itens.filter(venda__vendedor_id=vendedor_id)

    return itens, data_inicio, data_fim, categoria_id, vendedor_id


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def bi_avancado(request):
    from catalogo.models import Categoria

    itens, data_inicio, data_fim, categoria_id, vendedor_id = _aplicar_filtros(request)

    resumo = itens.aggregate(
        total_itens=Sum("quantidade"),
        total_valor=Sum(F("quantidade") * F("preco_unitario") - F("desconto")),
    )
    numero_vendas = itens.values("venda_id").distinct().count()

    return render(request, "relatorios/bi_avancado.html", {
        "itens": itens.order_by("-venda__fechada_em")[:200],
        "resumo": resumo,
        "numero_vendas": numero_vendas,
        "data_inicio": data_inicio,
        "data_fim": data_fim,
        "categoria_id": categoria_id,
        "vendedor_id": vendedor_id,
        "categorias": Categoria.objects.order_by("nome"),
        "vendedores": get_user_model().objects.filter(is_staff=True).order_by("username"),
        "clientes_por_estado_json": json.dumps(_clientes_por_estado()),
    })


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def bi_exportar_csv(request):
    itens, *_ = _aplicar_filtros(request)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="bi_vendas.csv"'
    writer = csv.writer(response)
    writer.writerow(["Data", "Cliente", "Vendedor", "Produto", "SKU", "Categoria", "Quantidade", "Preço unitário", "Subtotal"])
    for item in itens:
        writer.writerow([
            item.venda.fechada_em.strftime("%d/%m/%Y") if item.venda.fechada_em else "",
            item.venda.cliente.nome if item.venda.cliente else "",
            item.venda.vendedor.username if item.venda.vendedor else "",
            item.produto.nome, item.produto.sku,
            item.produto.categoria.nome if item.produto.categoria else "",
            item.quantidade, item.preco_unitario, item.subtotal,
        ])
    return response


@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def bi_exportar_pdf(request):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
    from reportlab.lib.styles import getSampleStyleSheet

    itens, data_inicio, data_fim, _, _ = _aplicar_filtros(request)

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    estilos = getSampleStyleSheet()

    elementos = [
        Paragraph("Belletti Cards Universe — Relatório de vendas", estilos["Title"]),
        Paragraph(f"Período: {data_inicio} a {data_fim}", estilos["Normal"]),
    ]

    dados_tabela = [["Data", "Produto", "Qtd", "Valor unit.", "Subtotal"]]
    for item in itens[:500]:
        dados_tabela.append([
            item.venda.fechada_em.strftime("%d/%m/%Y") if item.venda.fechada_em else "",
            item.produto.nome[:35],
            str(item.quantidade),
            f"R$ {item.preco_unitario:.2f}",
            f"R$ {item.subtotal:.2f}",
        ])

    tabela = Table(dados_tabela, repeatRows=1)
    tabela.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b6cf2")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    elementos.append(tabela)
    doc.build(elementos)

    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="bi_vendas.pdf"'
    return response
