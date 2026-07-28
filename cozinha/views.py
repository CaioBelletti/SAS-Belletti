import json
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    CategoriaPrato, ChamadoAtendente, ChecklistItemProducao, Comanda, EstacaoProducao,
    HistoricoStatusPedido, ItemPedidoCozinha, Mesa, PedidoCozinha, Prato,
)


def _get_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _contexto_cardapio(mesa=None):
    categorias = CategoriaPrato.objects.prefetch_related("pratos").all()
    pratos_sem_categoria = Prato.objects.filter(categoria__isnull=True, disponivel=True)
    return {"categorias": categorias, "pratos_sem_categoria": pratos_sem_categoria, "mesa": mesa}


def cardapio_publico(request):
    """Tela sem login pro cardápio genérico (balcão/retirada) — sem mesa vinculada."""
    return render(request, "cozinha/cardapio.html", _contexto_cardapio())


def confirmar_mesa(request, token):
    """
    Primeira tela ao ler o QR code de uma mesa: 'Você está na Mesa
    07?' — evita pedido feito por engano com QR antigo/foto salva.
    """
    mesa = get_object_or_404(Mesa, token_publico=token)
    if not mesa.ativa:
        return render(request, "cozinha/mesa_inativa.html", {"mesa": mesa})
    return render(request, "cozinha/confirmar_mesa.html", {"mesa": mesa})


def cardapio_mesa(request, token):
    """Cardápio já vinculado a uma mesa específica (depois da confirmação)."""
    mesa = get_object_or_404(Mesa, token_publico=token)
    if not mesa.ativa:
        return render(request, "cozinha/mesa_inativa.html", {"mesa": mesa})
    return render(request, "cozinha/cardapio.html", _contexto_cardapio(mesa=mesa))


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

    # Proteção simples contra pedido duplicado (clique duplo/rede lenta):
    # a mesma mesa (ou o mesmo IP, se for balcão) não pode mandar dois
    # pedidos em menos de 5 segundos.
    ip = _get_ip(request)
    mesa_token = dados.get("mesa_token")
    chave_throttle = f"cozinha_pedido_throttle:{mesa_token or ip}"
    if cache.get(chave_throttle):
        return JsonResponse({"ok": False, "erro": "Pedido já enviado — aguarde um instante antes de mandar outro."}, status=429)
    cache.set(chave_throttle, True, 5)

    mesa = None
    comanda = None
    if mesa_token:
        mesa = Mesa.objects.filter(token_publico=mesa_token, ativa=True).first()
        if not mesa:
            return JsonResponse({"ok": False, "erro": "Essa mesa não está mais disponível."}, status=400)
        comanda = mesa.comanda_aberta
        if not comanda:
            comanda = Comanda.objects.create(mesa=mesa)

    pedido = PedidoCozinha.objects.create(
        nome_para_chamar=nome,
        mesa_ou_local=(dados.get("mesa_ou_local") or "").strip() or (str(mesa) if mesa else ""),
        observacoes=(dados.get("observacoes") or "").strip(),
        mesa=mesa, comanda=comanda,
        ip=ip, dispositivo=request.META.get("HTTP_USER_AGENT", "")[:255],
    )

    for item in itens:
        prato = Prato.objects.filter(pk=item.get("prato_id"), disponivel=True).first()
        if not prato:
            continue
        item_pedido = ItemPedidoCozinha.objects.create(
            pedido=pedido, prato=prato,
            quantidade=max(int(item.get("quantidade") or 1), 1),
            preco_unitario=prato.preco,
            observacao=(item.get("observacao") or "").strip(),
        )
        etapas = list(prato.etapas_preparo.all())
        if etapas:
            ChecklistItemProducao.objects.bulk_create([
                ChecklistItemProducao(
                    item_pedido=item_pedido, descricao=etapa.descricao,
                    ordem=etapa.ordem, obrigatoria=etapa.obrigatoria,
                ) for etapa in etapas
            ])
        elif prato.instrucoes_preparo.strip():
            ChecklistItemProducao.objects.create(
                item_pedido=item_pedido, descricao=prato.instrucoes_preparo.strip(), ordem=0
            )

    if not pedido.itens.exists():
        pedido.delete()
        return JsonResponse({"ok": False, "erro": "Nenhum item válido no pedido."}, status=400)

    return JsonResponse({"ok": True, "pedido_id": pedido.id, "codigo": pedido.codigo_acompanhamento})


@require_POST
def chamar_atendente(request, token):
    mesa = get_object_or_404(Mesa, token_publico=token)
    tipo = request.POST.get("tipo", "atendente")
    if tipo not in dict(ChamadoAtendente.TIPO_CHOICES):
        tipo = "atendente"
    ChamadoAtendente.objects.create(mesa=mesa, tipo=tipo)
    return JsonResponse({"ok": True})


def acompanhar_pedido(request, codigo):
    """Tela sem login — o cliente acompanha o status do próprio pedido pelo link único."""
    pedido = get_object_or_404(PedidoCozinha, codigo_acompanhamento=codigo)
    return render(request, "cozinha/acompanhar.html", {"pedido": pedido})


@login_required
def painel_cozinha(request):
    """KDS/Kanban da cozinha, com filtros por estação, métricas e produção consolidada."""
    estacao_id = request.GET.get("estacao")
    base = (
        PedidoCozinha.objects.exclude(status__in=["entregue", "cancelado"])
        .select_related("mesa")
        .prefetch_related("itens__prato__estacao", "itens__checklist")
        .order_by("-prioridade", "criado_em")
    )
    if estacao_id and estacao_id.isdigit():
        base = base.filter(itens__prato__estacao_id=int(estacao_id)).distinct()

    pedidos_recebidos = [p for p in base if p.status == "recebido"]
    pedidos_preparo = [p for p in base if p.status == "em_preparo"]
    pedidos_prontos = [p for p in base if p.status == "pronto"]
    pedidos_em_entrega = [p for p in base if p.status == "em_entrega"]

    hoje = timezone.localdate()
    entregues_hoje_qs = (
        PedidoCozinha.objects.filter(status="entregue", entregue_em__date=hoje)
        .prefetch_related("itens__prato")
        .order_by("-entregue_em")
    )
    entregues_recentes = entregues_hoje_qs[:15]

    itens_ativos = ItemPedidoCozinha.objects.filter(
        pedido__status__in=["recebido", "em_preparo"]
    ).select_related("prato__estacao")
    if estacao_id and estacao_id.isdigit():
        itens_ativos = itens_ativos.filter(prato__estacao_id=int(estacao_id))

    resumo_map = {}
    for item in itens_ativos:
        chave = item.prato_id
        if chave not in resumo_map:
            resumo_map[chave] = {
                "prato": item.prato, "quantidade": 0,
                "estacao": item.prato.estacao,
            }
        resumo_map[chave]["quantidade"] += item.quantidade
    resumo_producao = sorted(
        resumo_map.values(), key=lambda x: (x["estacao"].ordem if x["estacao"] else 999, x["prato"].nome)
    )

    tempos = []
    for p in entregues_hoje_qs:
        if p.entregue_em:
            tempos.append((p.entregue_em - p.criado_em).total_seconds() / 60)
    tempo_medio = round(sum(tempos) / len(tempos), 1) if tempos else 0

    chamados_pendentes = ChamadoAtendente.objects.filter(atendido=False).select_related("mesa")
    estacoes = EstacaoProducao.objects.filter(ativa=True)
    contexto = {
        "pedidos_recebidos": pedidos_recebidos,
        "pedidos_preparo": pedidos_preparo,
        "pedidos_prontos": pedidos_prontos,
        "pedidos_em_entrega": pedidos_em_entrega,
        "entregues_hoje": entregues_recentes,
        "chamados_pendentes": chamados_pendentes,
        "estacoes": estacoes,
        "estacao_selecionada": int(estacao_id) if estacao_id and estacao_id.isdigit() else None,
        "resumo_producao": resumo_producao,
        "metricas": {
            "novos": len(pedidos_recebidos),
            "em_preparo": len(pedidos_preparo),
            "prontos": len(pedidos_prontos),
            "em_entrega": len(pedidos_em_entrega),
            "entregues_hoje": entregues_hoje_qs.count(),
            "tempo_medio": tempo_medio,
            "atrasados": sum(1 for p in list(pedidos_recebidos) + list(pedidos_preparo) if p.nivel_atraso in ["atrasado", "critico"]),
        },
    }
    return render(request, "cozinha/painel.html", contexto)


@login_required
@require_POST
def avancar_pedido(request, pedido_id):
    pedido = get_object_or_404(PedidoCozinha, pk=pedido_id)
    anterior = pedido.status
    pedido.atendido_por = request.user
    pedido.avancar_status()
    HistoricoStatusPedido.objects.create(
        pedido=pedido, status_anterior=anterior, status_novo=pedido.status, alterado_por=request.user
    )
    return JsonResponse({"ok": True, "novo_status": pedido.status})


@login_required
@require_POST
def alternar_checklist(request, checklist_id):
    checklist = get_object_or_404(ChecklistItemProducao, pk=checklist_id)
    checklist.concluido = not checklist.concluido
    checklist.concluido_em = timezone.now() if checklist.concluido else None
    checklist.concluido_por = request.user if checklist.concluido else None
    checklist.save(update_fields=["concluido", "concluido_em", "concluido_por"])

    item = checklist.item_pedido
    pendentes = item.checklist.filter(obrigatoria=True, concluido=False).exists()
    item.preparo_concluido = not pendentes
    item.concluido_em = timezone.now() if item.preparo_concluido else None
    if not item.iniciado_em:
        item.iniciado_em = timezone.now()
    item.save(update_fields=["preparo_concluido", "concluido_em", "iniciado_em"])
    return JsonResponse({"ok": True, "concluido": checklist.concluido, "item_concluido": item.preparo_concluido})


@login_required
def dados_painel(request):
    ativos = PedidoCozinha.objects.exclude(status__in=["entregue", "cancelado"])
    return JsonResponse({
        "recebidos": ativos.filter(status="recebido").count(),
        "em_preparo": ativos.filter(status="em_preparo").count(),
        "prontos": ativos.filter(status="pronto").count(),
        "em_entrega": ativos.filter(status="em_entrega").count(),
        "chamados": ChamadoAtendente.objects.filter(atendido=False).count(),
        "atualizado_em": timezone.localtime().strftime("%H:%M:%S"),
    })


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
@require_POST
def atender_chamado(request, chamado_id):
    chamado = get_object_or_404(ChamadoAtendente, pk=chamado_id)
    chamado.atendido = True
    chamado.atendido_em = timezone.now()
    chamado.save(update_fields=["atendido", "atendido_em"])
    return JsonResponse({"ok": True})



@login_required
def painel_garcom(request):
    """Painel operacional do salão: chamados, pedidos prontos e entregas."""
    chamados = ChamadoAtendente.objects.filter(atendido=False).select_related("mesa").order_by("criado_em")
    pedidos_prontos = (
        PedidoCozinha.objects.filter(status="pronto")
        .select_related("mesa")
        .prefetch_related("itens__prato")
        .order_by("pronto_em", "criado_em")
    )
    pedidos_em_entrega = (
        PedidoCozinha.objects.filter(status="em_entrega")
        .select_related("mesa")
        .prefetch_related("itens__prato")
        .order_by("em_entrega_em", "criado_em")
    )
    return render(request, "cozinha/painel_garcom.html", {
        "chamados": chamados,
        "pedidos_prontos": pedidos_prontos,
        "pedidos_em_entrega": pedidos_em_entrega,
    })


@login_required
def dados_garcom(request):
    """JSON para atualização e alertas sonoros do painel do garçom."""
    chamados = ChamadoAtendente.objects.filter(atendido=False).select_related("mesa").order_by("criado_em")
    prontos = PedidoCozinha.objects.filter(status="pronto").select_related("mesa").prefetch_related("itens__prato").order_by("pronto_em", "criado_em")
    entregas = PedidoCozinha.objects.filter(status="em_entrega").select_related("mesa").prefetch_related("itens__prato").order_by("em_entrega_em", "criado_em")

    def local_pedido(pedido):
        return str(pedido.mesa) if pedido.mesa else (pedido.mesa_ou_local or "Balcão")

    return JsonResponse({
        "chamados": [
            {
                "id": chamado.id,
                "tipo": chamado.tipo,
                "tipo_label": chamado.get_tipo_display(),
                "mesa": str(chamado.mesa),
                "criado_em": timezone.localtime(chamado.criado_em).strftime("%H:%M"),
            } for chamado in chamados
        ],
        "pedidos_prontos": [
            {
                "id": pedido.id,
                "local": local_pedido(pedido),
                "cliente": pedido.nome_para_chamar or "Cliente",
                "pronto_em": timezone.localtime(pedido.pronto_em or pedido.criado_em).strftime("%H:%M"),
                "itens": [f"{item.quantidade}x {item.prato.nome}" for item in pedido.itens.all()],
            } for pedido in prontos
        ],
        "pedidos_em_entrega": [
            {
                "id": pedido.id,
                "local": local_pedido(pedido),
                "cliente": pedido.nome_para_chamar or "Cliente",
                "em_entrega_em": timezone.localtime(pedido.em_entrega_em or pedido.criado_em).strftime("%H:%M"),
                "itens": [f"{item.quantidade}x {item.prato.nome}" for item in pedido.itens.all()],
            } for pedido in entregas
        ],
        "atualizado_em": timezone.localtime().strftime("%H:%M:%S"),
    })

@login_required
def mesas_abertas(request):
    """Tela pro PDV/equipe fechar a conta de uma mesa — vira uma Venda de verdade."""
    from .services import fechar_comanda

    if request.method == "POST":
        comanda = get_object_or_404(Comanda, pk=request.POST.get("comanda_id"))
        forma_pagamento = request.POST.get("forma_pagamento", "dinheiro")
        try:
            venda = fechar_comanda(comanda, forma_pagamento, request.user)
            messages.success(request, f"Comanda fechada — Venda #{venda.pk} gerada, R$ {venda.total:.2f}.")
        except ValueError as exc:
            messages.error(request, str(exc))
        return redirect("cozinha:mesas_abertas")

    comandas_abertas = Comanda.objects.filter(status="aberta").select_related("mesa").prefetch_related("pedidos__itens__prato")
    return render(request, "cozinha/mesas_abertas.html", {"comandas_abertas": comandas_abertas})


@login_required
def qrcode_cardapio(request):
    import io

    import qrcode

    url_cardapio = request.build_absolute_uri("/cardapio/")
    img = qrcode.make(url_cardapio)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
def qrcode_mesa(request, mesa_id):
    import io

    import qrcode

    mesa = get_object_or_404(Mesa, pk=mesa_id)
    url_mesa = request.build_absolute_uri(f"/cardapio/m/{mesa.token_publico}/")
    img = qrcode.make(url_mesa)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return HttpResponse(buffer.getvalue(), content_type="image/png")


@login_required
def qrcodes_todas_mesas_pdf(request):
    """Gera um PDF pronto pra imprimir, com uma placa de QR code por mesa ativa."""
    import io

    import qrcode
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import Image as RLImage
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.enums import TA_CENTER

    mesas = Mesa.objects.filter(ativa=True)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    estilos = getSampleStyleSheet()
    estilo_titulo = estilos["Title"]
    estilo_titulo.alignment = TA_CENTER
    estilo_sub = estilos["Normal"]
    estilo_sub.alignment = TA_CENTER

    elementos = []
    for mesa in mesas:
        url_mesa = request.build_absolute_uri(f"/cardapio/m/{mesa.token_publico}/")
        qr_img = qrcode.make(url_mesa)
        qr_buffer = io.BytesIO()
        qr_img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)

        elementos.append(Spacer(1, 3 * cm))
        elementos.append(Paragraph("BELLETTI CARDS UNIVERSE", estilo_titulo))
        elementos.append(Paragraph(str(mesa), estilo_titulo))
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(RLImage(qr_buffer, width=8 * cm, height=8 * cm))
        elementos.append(Spacer(1, 0.5 * cm))
        elementos.append(Paragraph("Aponte a câmera do celular e faça seu pedido", estilo_sub))
        elementos.append(PageBreak())

    if not elementos:
        elementos = [Paragraph("Nenhuma mesa ativa cadastrada ainda.", estilo_sub)]

    doc.build(elementos)
    buffer.seek(0)
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="qrcodes_mesas.pdf"'
    return response
