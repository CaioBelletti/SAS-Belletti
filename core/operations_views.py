from django.apps import apps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.http import require_GET

SCREENS = {
 "caixa": ("financeiro", "MovimentoCaixa", "Movimentações de caixa", ("data","tipo","descricao","valor","conciliado")),
 "pagar": ("financeiro", "ContaPagar", "Contas a pagar", ("descricao","fornecedor","valor","vencimento","status")),
 "receber": ("financeiro", "ContaReceber", "Contas a receber", ("descricao","cliente","valor","vencimento","status")),
 "metas": ("relatorios", "MetaMensal", "Metas mensais", ("mes","valor")),
 "automacoes": ("crm", "ConfiguracaoCRM", "Configurar automações", ("posvenda_ativo","posvenda_dias","aniversario_ativo","lead_parado_ativo","lead_parado_dias","recuperacao_carrinho_ativa","recuperacao_carrinho_horas")),
}
@login_required
@require_GET
def screen(request, kind):
    if kind not in SCREENS:
        raise Http404
    app, name, title, fields = SCREENS[kind]
    model = apps.get_model(app,name)
    if not request.user.has_perm(f"{app}.view_{model._meta.model_name}"):
        raise PermissionDenied
    qs = model.objects.order_by("-pk")
    page = Paginator(qs,30).get_page(request.GET.get("page"))
    rows = []
    for obj in page:
        row = []
        for field in fields:
            value = getattr(obj,field)
            display = getattr(obj,f"get_{field}_display",None)
            if display:
                value = display()
            elif isinstance(value,bool):
                value = "Ativo" if value else "Inativo"
            row.append(value)
        rows.append(row)
    return render(request,"operations/screen.html",{"title":title,"headers":[model._meta.get_field(f).verbose_name for f in fields],"rows":rows,"page_obj":page})
