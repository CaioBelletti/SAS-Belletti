from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from catalogo.models import Categoria, Produto
from vendas.models import Cliente
from suprimentos.models import Fornecedor

REGISTRY = {
    "clientes": (Cliente, "Clientes", "Cliente", ("nome","telefone","email","documento","data_nascimento","cep","logradouro","numero","complemento","bairro","cidade","uf")),
    "produtos": (Produto, "Produtos", "Produto", ("sku","codigo_interno","codigo_barras","ean","nome","marca","categoria","subcategoria","fornecedor","tags","edicao","numero_colecao","idioma","raridade","foil","reverse_holo","promo","estado_conservacao","descricao","imagem","peso_gramas","comprimento_cm","largura_cm","altura_cm","grading_empresa","grading_nota","grading_certificado","preco_custo","custo_frete","custo_impostos","preco_venda","preco_minimo","preco_maximo","margem_desejada","estoque_minimo","estoque_maximo","localizacao","lote","validade","numero_serie","ativo")),
    "fornecedores": (Fornecedor, "Fornecedores", "Fornecedor", ("nome", "documento", "telefone", "email", "avaliacao", "observacoes")),
    "categorias": (Categoria, "Categorias", "Categoria", ("nome", "jogo_tcg")),
}

def config(kind):
    if kind not in REGISTRY:
        raise Http404
    return REGISTRY[kind]

def allowed(user, model, action):
    return user.has_perm(f"{model._meta.app_label}.{action}_{model._meta.model_name}")

@login_required
@require_http_methods(["GET"])
def registration_list(request, kind):
    model, title, singular, fields = config(kind)
    if not allowed(request.user, model, "view"):
        raise PermissionDenied
    q = request.GET.get("q", "").strip()[:150]
    qs = model.objects.order_by("nome", "pk")
    if q:
        qs = qs.filter(Q(nome__icontains=q) | Q(sku__icontains=q)) if kind == "produtos" else qs.filter(nome__icontains=q)
    return render(request, "core/registration_list.html", {"kind":kind, "title":title, "singular":singular, "q":q, "page_obj":Paginator(qs,30).get_page(request.GET.get("page")), "can_add":allowed(request.user,model,"add"), "can_change":allowed(request.user,model,"change"), "can_delete":kind == "fornecedores" and allowed(request.user,model,"delete")})

@login_required
@require_http_methods(["GET", "POST"])
def registration_form(request, kind, pk=None):
    model, title, singular, fields = config(kind)
    if not allowed(request.user,model,"view") or not allowed(request.user,model,"change" if pk is not None else "add"):
        raise PermissionDenied
    obj = get_object_or_404(model,pk=pk) if pk is not None else None
    form_class = forms.modelform_factory(model,fields=fields)
    form = form_class(request.POST if request.method == "POST" else None,files=request.FILES if request.method == "POST" else None,instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request,"Cadastro salvo com sucesso.")
        return redirect("registration_list",kind=kind)
    return render(request,"core/registration_form.html",{"kind":kind,"title":title,"singular":singular,"form":form,"editing":obj is not None})

from django.db import transaction, IntegrityError
from django.db.models.deletion import Collector, ProtectedError, RestrictedError

def supplier_has_links(obj):
    for rel in obj._meta.related_objects:
        if rel.related_model._base_manager.filter(**{rel.field.name: obj}).exists():
            return True
    collector = Collector(using=obj._state.db)
    try:
        collector.collect([obj])
    except (ProtectedError, RestrictedError):
        return True
    return any(model is not type(obj) and objects for model, objects in collector.data.items()) or any(qs.exists() for qs in collector.fast_deletes)

@login_required
@require_http_methods(["GET", "POST"])
def supplier_delete(request, pk):
    if not allowed(request.user,Fornecedor,"view") or not allowed(request.user,Fornecedor,"delete"):
        raise PermissionDenied
    if request.method == "POST":
        try:
            with transaction.atomic():
                obj = get_object_or_404(Fornecedor.objects.select_for_update(),pk=pk)
                if supplier_has_links(obj):
                    messages.error(request,"Fornecedor possui registros vinculados e não pode ser excluído.")
                else:
                    obj.delete()
                    messages.success(request,"Fornecedor excluído.")
                    return redirect("registration_list",kind="fornecedores")
        except (ProtectedError, RestrictedError, IntegrityError):
            messages.error(request,"Exclusão bloqueada por registros vinculados.")
        return redirect("supplier_delete",pk=pk)
    obj = get_object_or_404(Fornecedor,pk=pk)
    return render(request,"core/supplier_delete.html",{"obj":obj,"blocked":supplier_has_links(obj)})
