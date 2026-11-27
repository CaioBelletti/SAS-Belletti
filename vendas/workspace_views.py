from django.contrib.auth.decorators import login_required, permission_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.views.decorators.http import require_GET
from .models import Venda

@login_required
@permission_required("vendas.view_venda", raise_exception=True)
@require_GET
def historico(request):
    qs = Venda.objects.select_related("cliente", "vendedor").order_by("-aberta_em", "-pk")
    q = request.GET.get("q", "").strip()[:150]
    status = request.GET.get("status", "")
    if q:
        condition = Q(cliente__nome__icontains=q)
        if q.isdecimal() and len(q) < 19:
            condition |= Q(pk=int(q))
        qs = qs.filter(condition)
    if status in dict(Venda.STATUS_CHOICES):
        qs = qs.filter(status=status)
    else:
        status = ""
    return render(request, "vendas/historico.html", {"page_obj":Paginator(qs,30).get_page(request.GET.get("page")), "q":q, "status":status, "statuses":Venda.STATUS_CHOICES})
