from datetime import date
from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import MovimentacaoEstoque

@login_required
@permission_required("catalogo.view_movimentacaoestoque", raise_exception=True)
def movimentacoes(request):
    qs = MovimentacaoEstoque.objects.select_related("produto").order_by("-criado_em", "-pk")
    q = request.GET.get("q", "").strip()[:200]
    tipo = request.GET.get("tipo", "")
    if q:
        qs = qs.filter(Q(produto__nome__icontains=q) | Q(produto__sku__icontains=q) | Q(motivo__icontains=q))
    if tipo in dict(MovimentacaoEstoque.TIPO_CHOICES):
        qs = qs.filter(tipo=tipo)
    else:
        tipo = ""
    datas = {}
    for param, lookup in (("inicio", "criado_em__date__gte"), ("fim", "criado_em__date__lte")):
        try:
            value = date.fromisoformat(request.GET.get(param, ""))
        except ValueError:
            continue
        datas[param] = value.isoformat()
        qs = qs.filter(**{lookup: value})
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "catalogo/movimentacoes.html", {"page_obj": page, "q": q, "tipo": tipo, "tipos": MovimentacaoEstoque.TIPO_CHOICES, "datas": datas, "querystring": params.urlencode()})
