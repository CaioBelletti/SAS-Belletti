import json
import uuid
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Count, Max, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import (
    CategoriaPrato, ChamadoAtendente, ChecklistItemProducao, Comanda, EstacaoProducao,
    HistoricoStatusPedido, ItemPedidoCozinha, Mesa, PedidoCozinha, Prato,
    ParticipanteMesa, PromocaoCardapio, AvaliacaoMesa,
)


def _get_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _contexto_cardapio(mesa=None):
    categorias = CategoriaPrato.objects.prefetch_related(
        "pratos"
    ).filter(pratos__disponivel=True).distinct()
    pratos_sem_categoria = Prato.objects.filter(
        categoria__isnull=True,
        disponivel=True,
    )

    comanda = None
    pedidos_mesa = PedidoCozinha.objects.none()
    if mesa:
        comanda = mesa.comanda_aberta
        if comanda:
            pedidos_mesa = (
                comanda.pedidos.exclude(status="cancelado")
                .prefetch_related("itens__prato")
                .order_by("-criado_em")
            )

    participantes = comanda.participantes.filter(ativo=True).order_by("entrou_em") if comanda else ParticipanteMesa.objects.none()
    promocoes = [p for p in PromocaoCardapio.objects.prefetch_related("itens__prato").filter(ativa=True, destaque=True) if p.disponivel_agora]
    return {
        "categorias": categorias,
        "pratos_sem_categoria": pratos_sem_categoria,
        "mesa": mesa,
        "comanda": comanda,
        "pedidos_mesa": pedidos_mesa,
        "participantes": participantes,
        "promocoes": promocoes,
    }


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

    participante = None
    participante_token = dados.get("participante_token")
    if comanda:
        try:
            token_valido = participante_token or uuid.uuid4()
            participante, _ = ParticipanteMesa.objects.get_or_create(
                comanda=comanda, token_dispositivo=token_valido,
                defaults={"nome": nome},
            )
            if participante.nome != nome:
                participante.nome = nome
                participante.save(update_fields=["nome"])
        except (ValueError, TypeError):
            participante = ParticipanteMesa.objects.create(comanda=comanda, nome=nome)

    pedido = PedidoCozinha.objects.create(
        participante=participante,
        nome_para_chamar=nome,
        mesa_ou_local=(dados.get("mesa_ou_local") or "").strip() or (str(mesa) if mesa else ""),
        observacoes=(dados.get("observacoes") or "").strip(),
        mesa=mesa, comanda=comanda,
        ip=ip, dispositivo=request.META.get("HTTP_USER_AGENT", "")[:255],
    )

    from .models import AdicionalPrato, ItemPedidoAdicional

    def criar_item(prato, quantidade, preco_unitario, observacao="", adicional_ids=None):
        item_pedido = ItemPedidoCozinha.objects.create(
            pedido=pedido, prato=prato, quantidade=quantidade,
            preco_unitario=preco_unitario, observacao=observacao,
        )
        if adicional_ids:
            adicionais = AdicionalPrato.objects.filter(
                pk__in=adicional_ids, prato=prato, disponivel=True
            )
            ItemPedidoAdicional.objects.bulk_create([
                ItemPedidoAdicional(item_pedido=item_pedido, adicional=a, nome=a.nome, preco_extra=a.preco_extra)
                for a in adicionais
            ])
        etapas = list(prato.etapas_preparo.all())
        if etapas:
            ChecklistItemProducao.objects.bulk_create([
                ChecklistItemProducao(item_pedido=item_pedido, descricao=e.descricao, ordem=e.ordem, obrigatoria=e.obrigatoria)
                for e in etapas
            ])
        elif prato.instrucoes_preparo.strip():
            ChecklistItemProducao.objects.create(item_pedido=item_pedido, descricao=prato.instrucoes_preparo.strip(), ordem=0)

    for item in itens:
        quantidade_carrinho = max(int(item.get("quantidade") or 1), 1)
        promocao_id = item.get("promocao_id")
        if promocao_id:
            promocao = PromocaoCardapio.objects.prefetch_related("itens__prato").filter(pk=promocao_id, ativa=True).first()
            if not promocao or not promocao.disponivel_agora:
                continue
            promo_itens = list(promocao.itens.all())
            total_regular = sum((pi.prato.preco * pi.quantidade for pi in promo_itens), Decimal("0"))
            restante = promocao.preco_promocional
            for idx, pi in enumerate(promo_itens):
                if idx == len(promo_itens)-1:
                    preco_linha = restante
                else:
                    preco_linha = (promocao.preco_promocional * (pi.prato.preco*pi.quantidade) / total_regular).quantize(Decimal("0.01")) if total_regular else Decimal("0")
                    restante -= preco_linha
                unitario = (preco_linha / pi.quantidade).quantize(Decimal("0.01")) if pi.quantidade else Decimal("0")
                criar_item(pi.prato, pi.quantidade * quantidade_carrinho, unitario, f"Promoção: {promocao.titulo}")
            continue
        prato = Prato.objects.filter(pk=item.get("prato_id"), disponivel=True).first()
        if prato:
            criar_item(
                prato, quantidade_carrinho, prato.preco, (item.get("observacao") or "").strip(),
                adicional_ids=item.get("adicionais") or [],
            )

    if not pedido.itens.exists():
        pedido.delete()
        return JsonResponse({"ok": False, "erro": "Nenhum item válido no pedido."}, status=400)

    return JsonResponse({
        "ok": True,
        "pedido_id": pedido.id,
        "codigo": pedido.codigo_acompanhamento,
        "redirect_url": reverse("acompanhar_pedido", kwargs={"codigo": pedido.codigo_acompanhamento}),
        "participante_token": str(participante.token_dispositivo) if participante else None,
    })


@require_POST
def chamar_atendente(request, token):
    mesa = get_object_or_404(Mesa, token_publico=token)
    tipo = request.POST.get("tipo", "atendente")
    if tipo not in dict(ChamadoAtendente.TIPO_CHOICES):
        tipo = "atendente"
    ChamadoAtendente.objects.create(mesa=mesa, tipo=tipo)
    return JsonResponse({"ok": True})


def acompanhar_pedido(request, codigo):
    """Tela sem login — acompanhamento, atalhos e histórico da comanda."""
    pedido = get_object_or_404(
        PedidoCozinha.objects.select_related("mesa", "comanda").prefetch_related(
            "itens__prato"
        ),
        codigo_acompanhamento=codigo,
    )
    pedidos_comanda = PedidoCozinha.objects.none()
    if pedido.comanda_id:
        pedidos_comanda = (
            pedido.comanda.pedidos.exclude(status="cancelado")
            .prefetch_related("itens__prato")
            .order_by("-criado_em")
        )
    return render(
        request,
        "cozinha/acompanhar.html",
        {
            "pedido": pedido,
            "pedidos_comanda": pedidos_comanda,
            "comanda": pedido.comanda,
        },
    )


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
    """Tela pro PDV/equipe fechar a conta de uma mesa — vira uma Venda de verdade (junto ou dividida)."""
    from .services import DivisaoInvalidaError, fechar_comanda, fechar_comanda_dividida

    if request.method == "POST":
        comanda = get_object_or_404(Comanda, pk=request.POST.get("comanda_id"))
        acao = request.POST.get("acao", "fechar_junto")

        try:
            if acao == "dividir_igual":
                partes = max(int(request.POST.get("partes") or 1), 1)
                valor_parte = (comanda.valor_total / partes).quantize(Decimal("0.01"))
                divisoes = [{"descricao": f"Parte {i+1} de {partes}", "valor": valor_parte, "forma_pagamento": request.POST.get("forma_pagamento", "dinheiro")} for i in range(partes)]
                diferenca = comanda.valor_total - (valor_parte * partes)
                if diferenca:
                    divisoes[-1]["valor"] += diferenca
                vendas = fechar_comanda_dividida(comanda, divisoes, request.user)
                messages.success(request, f"Comanda dividida em {len(vendas)} parte(s) — {len(vendas)} venda(s) geradas.")
            elif acao == "dividir_pessoa":
                divisoes = []
                for participante in comanda.participantes.filter(ativo=True):
                    valor_pessoa = participante.total_consumido
                    if valor_pessoa > 0:
                        divisoes.append({
                            "descricao": participante.nome, "valor": valor_pessoa,
                            "forma_pagamento": request.POST.get("forma_pagamento", "dinheiro"),
                        })
                vendas = fechar_comanda_dividida(comanda, divisoes, request.user)
                messages.success(request, f"Comanda dividida por pessoa — {len(vendas)} venda(s) geradas.")
            else:
                forma_pagamento = request.POST.get("forma_pagamento", "dinheiro")
                venda = fechar_comanda(comanda, forma_pagamento, request.user)
                messages.success(request, f"Comanda fechada — Venda #{venda.pk} gerada, R$ {venda.total:.2f}.")
        except (ValueError, DivisaoInvalidaError) as exc:
            messages.error(request, str(exc))
        return redirect("cozinha:mesas_abertas")

    comandas_abertas = (
        Comanda.objects.filter(status="aberta")
        .select_related("mesa")
        .prefetch_related("pedidos__itens__prato", "participantes")
    )
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


@require_POST
def avaliar_experiencia(request, token):
    mesa = get_object_or_404(Mesa, token_publico=token, ativa=True)
    comanda = mesa.comanda_aberta
    if not comanda:
        return JsonResponse({"ok": False, "erro": "Não há comanda aberta para esta mesa."}, status=400)
    try:
        dados = json.loads(request.body)
        comida = int(dados.get("nota_comida"))
        atendimento = int(dados.get("nota_atendimento"))
    except (ValueError, TypeError, json.JSONDecodeError):
        return JsonResponse({"ok": False, "erro": "Avaliação inválida."}, status=400)
    if comida not in range(1,6) or atendimento not in range(1,6):
        return JsonResponse({"ok": False, "erro": "As notas devem ser de 1 a 5."}, status=400)
    participante = None
    token_participante = dados.get("participante_token")
    if token_participante:
        participante = ParticipanteMesa.objects.filter(comanda=comanda, token_dispositivo=token_participante).first()
    AvaliacaoMesa.objects.create(
        comanda=comanda, participante=participante,
        nota_comida=comida, nota_atendimento=atendimento,
        comentario=(dados.get("comentario") or "").strip()[:500],
    )
    return JsonResponse({"ok": True})


def preferencias_mesa(request, token):
    mesa = get_object_or_404(Mesa, token_publico=token, ativa=True)
    comanda = mesa.comanda_aberta
    token_participante = request.GET.get("participante_token")
    participante = None
    if comanda and token_participante:
        participante = ParticipanteMesa.objects.filter(comanda=comanda, token_dispositivo=token_participante).first()
    favoritos = []
    if participante:
        qs = (ItemPedidoCozinha.objects.filter(pedido__participante=participante)
              .values("prato_id", "prato__nome", "prato__preco")
              .annotate(total=Sum("quantidade")).filter(total__gte=3).order_by("-total")[:6])
        favoritos = list(qs)
    return JsonResponse({
        "ok": True,
        "participante": participante.nome if participante else None,
        "favoritos": favoritos,
        "jogadores": list(comanda.participantes.filter(ativo=True).values("nome", "token_dispositivo")) if comanda else [],
    })


@login_required
def avaliacoes_view(request):
    """Painel com o resumo das avaliações deixadas pelos clientes (nota da comida/atendimento + comentário)."""
    from .models import AvaliacaoMesa

    todas = AvaliacaoMesa.objects.select_related("comanda__mesa", "participante").all()

    resumo = todas.aggregate(
        media_comida=Avg("nota_comida"), media_atendimento=Avg("nota_atendimento"), total=Count("id"),
    )
    distribuicao_comida = {
        nota: todas.filter(nota_comida=nota).count() for nota in (5, 4, 3, 2, 1)
    }

    baixas = todas.filter(Q(nota_comida__lte=2) | Q(nota_atendimento__lte=2))[:20]
    recentes = todas[:100]

    return render(request, "cozinha/avaliacoes.html", {
        "resumo": resumo,
        "distribuicao_comida": distribuicao_comida,
        "avaliacoes_baixas": baixas,
        "avaliacoes_recentes": recentes,
    })
