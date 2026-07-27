import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from .models import CategoriaPrato, ItemPedidoCozinha, PedidoCozinha, Prato


def cardapio_publico(request):
    """Tela sem login, pensada pra ser acessada via QR code na mesa/balcão."""
    categorias = CategoriaPrato.objects.prefetch_related("pratos").all()
    pratos_sem_categoria = Prato.objects.filter(categoria__isnull=True, disponivel=True)
    return render(request, "cozinha/cardapio.html", {
        "categorias": categorias,
        "pratos_sem_categoria": pratos_sem_categoria,
    })


@require_POST
def fazer_pedido(request):
    """Recebe o pedido montado no cardápio público e cria na fila da cozinha."""
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    itens = dados.get("itens", [])
    if not itens:
        return JsonResponse({"ok": False, "erro": "Adicione pelo menos um item ao pedido."}, status=400)

    nome = (dados.get("nome") or "").strip()
    if not nome:
        return JsonResponse({"ok": False, "erro": "Informe seu nome pra chamarmos quando ficar pronto."}, status=400)

    pedido = PedidoCozinha.objects.create(
        nome_para_chamar=nome,
        mesa_ou_local=(dados.get("mesa_ou_local") or "").strip(),
        observacoes=(dados.get("observacoes") or "").strip(),
    )

    for item in itens:
        prato = Prato.objects.filter(pk=item.get("prato_id"), disponivel=True).first()
        if not prato:
            continue
        ItemPedidoCozinha.objects.create(
            pedido=pedido, prato=prato,
            quantidade=max(int(item.get("quantidade") or 1), 1),
            preco_unitario=prato.preco,
            observacao=(item.get("observacao") or "").strip(),
        )

    if not pedido.itens.exists():
        pedido.delete()
        return JsonResponse({"ok": False, "erro": "Nenhum item válido no pedido."}, status=400)

    return JsonResponse({"ok": True, "pedido_id": pedido.id, "codigo": pedido.codigo_acompanhamento})


def acompanhar_pedido(request, codigo):
    """Tela sem login — o cliente acompanha o status do próprio pedido pelo link único."""
    pedido = get_object_or_404(PedidoCozinha, codigo_acompanhamento=codigo)
    return render(request, "cozinha/acompanhar.html", {"pedido": pedido})


@login_required
def painel_cozinha(request):
    """Painel da equipe — pedidos ordenados por prioridade e depois por horário."""
    pedidos_ativos = (
        PedidoCozinha.objects.exclude(status__in=["entregue", "cancelado"])
        .prefetch_related("itens__prato")
        .order_by("-prioridade", "criado_em")
    )
    entregues_hoje = (
        PedidoCozinha.objects.filter(status="entregue")
        .prefetch_related("itens__prato")
        .order_by("-entregue_em")[:15]
    )
    return render(request, "cozinha/painel.html", {
        "pedidos_ativos": pedidos_ativos,
        "entregues_hoje": entregues_hoje,
    })


@login_required
@require_POST
def avancar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoCozinha, pk=pedido_id)
    pedido.atendido_por = request.user
    pedido.avancar_status()
    return JsonResponse({"ok": True, "novo_status": pedido.status})


@login_required
@require_POST
def mudar_prioridade(request, pedido_id):
    pedido = get_object_or_404(PedidoCozinha, pk=pedido_id)
    nova_prioridade = request.POST.get("prioridade")
    if nova_prioridade in ("1", "2", "3"):
        pedido.prioridade = int(nova_prioridade)
        pedido.save(update_fields=["prioridade"])
    return JsonResponse({"ok": True, "prioridade": pedido.prioridade})


@login_required
@require_POST
def cancelar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoCozinha, pk=pedido_id)
    pedido.status = "cancelado"
    pedido.save(update_fields=["status"])
    return JsonResponse({"ok": True})


@login_required
def qrcode_cardapio(request):
    import io

    import qrcode
    from django.http import HttpResponse

    url_cardapio = request.build_absolute_uri("/cardapio/")
    img = qrcode.make(url_cardapio)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")
