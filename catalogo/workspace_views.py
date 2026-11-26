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

from django import forms
from django.db import transaction
from django.shortcuts import redirect
from .models import Produto

class LancamentoForm(forms.Form):
    sku = forms.CharField(label="SKU do produto", max_length=50)
    tipo = forms.ChoiceField(choices=MovimentacaoEstoque.TIPO_CHOICES)
    quantidade = forms.IntegerField(min_value=0, label="Quantidade (no ajuste, saldo final)")
    categoria = forms.ChoiceField(choices=MovimentacaoEstoque.CATEGORIA_CHOICES, required=False)
    motivo = forms.CharField(max_length=200, required=True)

@login_required
@permission_required(("catalogo.view_movimentacaoestoque", "catalogo.add_movimentacaoestoque"), raise_exception=True)
def novo_lancamento(request):
    form = LancamentoForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        with transaction.atomic():
            produto = Produto.objects.select_for_update().filter(sku=d["sku"]).first()
            if produto is None:
                form.add_error("sku", "SKU não encontrado.")
            elif d["tipo"] != "ajuste" and d["quantidade"] == 0:
                form.add_error("quantidade", "Informe uma quantidade maior que zero.")
            elif d["tipo"] == "saida" and d["quantidade"] > produto.estoque_atual:
                form.add_error("quantidade", "Saldo insuficiente.")
            elif d["tipo"] == "ajuste" and d["quantidade"] == produto.estoque_atual:
                form.add_error("quantidade", "O saldo já possui esse valor.")
            else:
                quantidade = d["quantidade"]
                if d["tipo"] == "ajuste":
                    quantidade = abs(d["quantidade"] - produto.estoque_atual)
                    Produto.objects.filter(pk=produto.pk).update(estoque_atual=d["quantidade"])
                MovimentacaoEstoque.objects.create(produto=produto, tipo=d["tipo"], quantidade=quantidade, categoria=d["categoria"], motivo=d["motivo"])
                return redirect("catalogo:movimentacoes")
    return render(request, "catalogo/novo_lancamento.html", {"form": form})
