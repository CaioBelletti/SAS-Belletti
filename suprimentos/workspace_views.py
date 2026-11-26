from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from .models import OrdemCompra

@login_required
@permission_required("suprimentos.view_ordemcompra", raise_exception=True)
def ordens(request):
    qs = OrdemCompra.objects.select_related("fornecedor").prefetch_related("itens").order_by("-criada_em", "-pk")
    q = request.GET.get("q", "").strip()[:200]
    status = request.GET.get("status", "")
    if q:
        filtro = Q(fornecedor__nome__icontains=q)
        if q.isascii() and q.isdigit() and len(q) < 19:
            filtro |= Q(pk=int(q))
        qs = qs.filter(filtro)
    if status in dict(OrdemCompra.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ""
    params = request.GET.copy()
    params.pop("page", None)
    return render(request, "suprimentos/ordens.html", {"page_obj": Paginator(qs, 30).get_page(request.GET.get("page")), "q": q, "status": status, "statuses": OrdemCompra.STATUS_CHOICES, "querystring": params.urlencode()})

@login_required
@permission_required("suprimentos.view_ordemcompra", raise_exception=True)
def ordem_detalhe(request, pk):
    ordem = get_object_or_404(OrdemCompra.objects.select_related("fornecedor").prefetch_related("itens__produto"), pk=pk)
    return render(request, "suprimentos/ordem_detalhe.html", {"ordem": ordem})
