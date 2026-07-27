import json
from decimal import Decimal, InvalidOperation

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from catalogo.models import Produto

from .models import Cliente, ItemVenda, PagamentoVenda, Venda, get_config_fidelidade
from .services import (
    CupomInvalidoError,
    EstoqueInsuficienteError,
    PontosInsuficientesError,
    ValeInvalidoError,
    fechar_venda,
)


@login_required
def pdv(request):
    clientes = Cliente.objects.order_by("nome")
    clientes_pontos = {
        str(c.id): {
            "pontos": c.pontos_fidelidade,
            "valor": str(c.valor_pontos_em_reais),
            "credito": str(c.saldo_credito),
            "blacklist": c.blacklist,
            "blacklist_motivo": c.blacklist_motivo,
        }
        for c in clientes
    }
    config_fidelidade = get_config_fidelidade()
    return render(request, "vendas/pdv.html", {
        "clientes": clientes,
        "clientes_pontos_json": json.dumps(clientes_pontos),
        "valor_resgate_ponto": config_fidelidade.valor_resgate_ponto,
        "fidelidade_ativa": config_fidelidade.ativo,
    })


@login_required
@require_GET
def api_buscar_produtos(request):
    termo = request.GET.get("q", "").strip()
    if len(termo) < 1:
        return JsonResponse({"produtos": []})

    # Match exato de código de barras ou SKU (fluxo do leitor de código de
    # barras: ele "digita" o código inteiro de uma vez) tem prioridade —
    # se achar, retorna só ele, pra já poder adicionar direto sem ambiguidade.
    exato = Produto.objects.filter(ativo=True).filter(
        Q(codigo_barras__iexact=termo) | Q(sku__iexact=termo)
    ).first()
    if exato:
        return JsonResponse({
            "produtos": [{
                "id": exato.id,
                "sku": exato.sku,
                "nome": exato.nome,
                "preco_venda": str(exato.preco_venda),
                "estoque_atual": exato.estoque_atual,
                "estoque_disponivel": exato.estoque_disponivel,
                "grading": exato.grading_display,
                "variante": exato.variante_display,
            }],
            "match_exato": True,
        })

    produtos = (
        Produto.objects.filter(ativo=True)
        .filter(Q(sku__icontains=termo) | Q(nome__icontains=termo) | Q(codigo_barras__icontains=termo))
        .distinct()[:8]
    )

    return JsonResponse({
        "produtos": [
            {
                "id": p.id,
                "sku": p.sku,
                "nome": p.nome,
                "preco_venda": str(p.preco_venda),
                "estoque_atual": p.estoque_atual,
                "estoque_disponivel": p.estoque_disponivel,
                "grading": p.grading_display,
                "variante": p.variante_display,
            }
            for p in produtos
        ],
        "match_exato": False,
    })


@login_required
@require_GET
def api_validar_cupom(request):
    from .models import CupomDesconto

    codigo = request.GET.get("codigo", "").strip()
    try:
        subtotal = Decimal(str(request.GET.get("subtotal") or "0"))
    except InvalidOperation:
        subtotal = Decimal("0")

    cupom = CupomDesconto.objects.filter(codigo__iexact=codigo).first()
    if not cupom:
        return JsonResponse({"valido": False, "erro": "Cupom não encontrado."})
    if not cupom.valido:
        return JsonResponse({"valido": False, "erro": "Esse cupom não é mais válido."})

    desconto_calculado = cupom.calcular_desconto(subtotal)
    return JsonResponse({
        "valido": True,
        "cupom_id": cupom.id,
        "codigo": cupom.codigo,
        "tipo": cupom.tipo,
        "valor": str(cupom.valor),
        "desconto_calculado": str(desconto_calculado),
    })


@login_required
@require_GET
def api_validar_vale(request):
    from .models import Vale

    codigo = request.GET.get("codigo", "").strip()
    vale = Vale.objects.filter(codigo__iexact=codigo).first()
    if not vale:
        return JsonResponse({"valido": False, "erro": "Vale não encontrado."})
    if not vale.valido:
        return JsonResponse({"valido": False, "erro": "Esse vale está sem saldo ou inativo."})

    return JsonResponse({
        "valido": True, "vale_id": vale.id, "codigo": vale.codigo, "saldo": str(vale.saldo),
    })


@login_required
@require_POST
def api_salvar_orcamento(request):
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    itens = dados.get("itens", [])
    if not itens:
        return JsonResponse({"ok": False, "erro": "O carrinho está vazio."}, status=400)

    cliente_id = dados.get("cliente_id") or None
    observacoes = str(dados.get("observacoes") or "").strip()[:2000]
    try:
        desconto = Decimal(str(dados.get("desconto") or "0"))
    except InvalidOperation:
        desconto = Decimal("0")

    try:
        with transaction.atomic():
            venda = Venda.objects.create(
                cliente_id=cliente_id,
                desconto=desconto,
                observacoes=observacoes,
                vendedor=request.user,
                status="orcamento",
            )
            for item in itens:
                produto = Produto.objects.get(pk=item["produto_id"])
                ItemVenda.objects.create(
                    venda=venda,
                    produto=produto,
                    quantidade=int(item["quantidade"]),
                    preco_unitario=Decimal(str(item["preco_unitario"])),
                )
    except Produto.DoesNotExist:
        return JsonResponse({"ok": False, "erro": "Produto não encontrado."}, status=400)
    except Exception:
        return JsonResponse({"ok": False, "erro": "Não foi possível salvar o orçamento."}, status=400)

    return JsonResponse({"ok": True, "venda_id": venda.id, "total": str(venda.total)})


def _processar_venda_payload(dados, usuario, uuid_offline=None):
    """
    Núcleo de validação + criação de uma venda a partir de um payload
    (o mesmo formato usado tanto pelo finalizar normal quanto pela
    sincronização de vendas feitas no modo offline do PDV). Levanta
    uma das exceções conhecidas em caso de problema — quem chama
    decide como responder (JSON de erro, ou marcar como pendente de
    revisão manual, no caso do offline).
    """
    itens = dados.get("itens", [])
    if not itens:
        raise ValueError("O carrinho está vazio.")

    pagamentos_dados = dados.get("pagamentos", [])
    if not pagamentos_dados:
        raise ValueError("Adicione ao menos um pagamento.")

    formas_validas = dict(Venda.FORMA_PAGAMENTO_CHOICES)
    for p in pagamentos_dados:
        if p.get("forma_pagamento") not in formas_validas:
            raise ValueError("Forma de pagamento inválida.")
        if p.get("forma_pagamento") == "vale" and not p.get("vale_id"):
            raise ValueError("Pagamento em vale precisa informar qual vale.")

    try:
        desconto = Decimal(str(dados.get("desconto") or "0"))
        acrescimo = Decimal(str(dados.get("acrescimo") or "0"))
    except InvalidOperation:
        raise ValueError("Desconto ou acréscimo inválido.")

    observacoes = str(dados.get("observacoes") or "").strip()[:2000]
    cliente_id = dados.get("cliente_id") or None
    canal = dados.get("canal") if dados.get("canal") in dict(Venda.CANAL_CHOICES) else "fisica"

    try:
        pontos_resgatar = int(dados.get("pontos_resgatar") or 0)
    except (ValueError, TypeError):
        pontos_resgatar = 0

    desconto_pontos = Decimal("0")
    if pontos_resgatar > 0:
        config = get_config_fidelidade()
        desconto_pontos = pontos_resgatar * config.valor_resgate_ponto

    try:
        credito_usar = Decimal(str(dados.get("credito_usar") or "0"))
    except InvalidOperation:
        raise ValueError("Valor de crédito inválido.")
    if credito_usar < 0:
        credito_usar = Decimal("0")

    from .models import CupomDesconto
    cupom = None
    desconto_cupom = Decimal("0")
    cupom_id = dados.get("cupom_id")
    if cupom_id:
        cupom = CupomDesconto.objects.filter(pk=cupom_id).first()
        if not cupom or not cupom.valido:
            raise CupomInvalidoError("Cupom inválido ou expirado.")
        subtotal_bruto = sum(
            (Decimal(str(i["preco_unitario"])) * int(i["quantidade"]) for i in itens), Decimal("0")
        )
        desconto_cupom = cupom.calcular_desconto(subtotal_bruto)

    with transaction.atomic():
        venda = Venda.objects.create(
            cliente_id=cliente_id,
            desconto=desconto + desconto_pontos + credito_usar + desconto_cupom,
            acrescimo=acrescimo,
            observacoes=observacoes,
            vendedor=usuario,
            canal=canal,
            pontos_resgatados=pontos_resgatar,
            credito_usado=credito_usar,
            cupom=cupom,
            uuid_offline=uuid_offline,
        )
        for item in itens:
            produto = Produto.objects.select_for_update().get(pk=item["produto_id"])
            try:
                desconto_item = Decimal(str(item.get("desconto") or "0"))
            except InvalidOperation:
                desconto_item = Decimal("0")
            ItemVenda.objects.create(
                venda=venda,
                produto=produto,
                quantidade=int(item["quantidade"]),
                preco_unitario=Decimal(str(item["preco_unitario"])),
                desconto=desconto_item,
            )
        for p in pagamentos_dados:
            PagamentoVenda.objects.create(
                venda=venda,
                forma_pagamento=p["forma_pagamento"],
                valor=Decimal(str(p["valor"])),
                parcelas=int(p.get("parcelas") or 1),
                vale_id=p.get("vale_id") or None,
            )

        from aprovacoes.services import precisa_aprovacao, solicitar_aprovacao
        total_desconto = venda.desconto + sum((i.desconto for i in venda.itens.all()), Decimal("0"))
        if precisa_aprovacao("desconto", total_desconto):
            venda.status = "pendente_aprovacao"
            venda.save(update_fields=["status"])
            solicitar_aprovacao(
                "desconto", venda, total_desconto,
                f"Venda #{venda.pk} — desconto de R$ {total_desconto}",
                solicitante=usuario,
            )
        else:
            fechar_venda(venda)

    return venda


@login_required
@require_POST
def api_finalizar_venda(request):
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    try:
        venda = _processar_venda_payload(dados, request.user)
    except (EstoqueInsuficienteError, PontosInsuficientesError, CupomInvalidoError, ValeInvalidoError, ValueError) as exc:
        return JsonResponse({"ok": False, "erro": str(exc)}, status=400)
    except Produto.DoesNotExist:
        return JsonResponse({"ok": False, "erro": "Produto não encontrado."}, status=400)
    except (KeyError, TypeError):
        return JsonResponse({"ok": False, "erro": "Dados da venda incompletos ou mal formatados."}, status=400)
    except Exception:
        return JsonResponse({"ok": False, "erro": "Não foi possível concluir a venda."}, status=400)

    if venda.status == "pendente_aprovacao":
        from auditoria.models import registrar
        registrar(request.user, "venda_pendente_aprovacao", f"Venda #{venda.id} aguardando aprovação de desconto", request=request)
        return JsonResponse({
            "ok": True, "pendente_aprovacao": True, "venda_id": venda.id,
            "mensagem": "Desconto acima do permitido — venda enviada pra aprovação do gerente.",
        })

    from auditoria.models import registrar
    registrar(request.user, "venda_fechada", f"Venda #{venda.id} — R$ {venda.total}", request=request)

    return JsonResponse({"ok": True, "venda_id": venda.id, "total": str(venda.total)})


@login_required
@require_GET
def api_produtos_offline(request):
    """Snapshot de todos os produtos ativos, pra guardar no IndexedDB do navegador e buscar sem internet."""
    produtos = Produto.objects.filter(ativo=True).select_related("categoria")
    dados = [
        {
            "id": p.id, "sku": p.sku, "nome": p.nome,
            "preco_venda": str(p.preco_venda), "estoque_atual": p.estoque_atual,
            "grading": p.grading_display, "variante": p.variante_display,
            "codigo_barras": p.codigo_barras or "", "ean": p.ean or "",
        }
        for p in produtos
    ]
    return JsonResponse({"produtos": dados, "gerado_em": timezone.now().isoformat()})


@login_required
@require_POST
def api_sincronizar_offline(request):
    """
    Recebe uma lista de vendas feitas no modo offline do PDV e tenta
    processar cada uma. Usa o uuid_offline como chave de idempotência
    — se a mesma venda já foi sincronizada antes (ex: a internet caiu
    no meio da resposta e o navegador tentou de novo), não duplica.
    Se der conflito (ex: estoque insuficiente porque já vendeu em
    outro terminal enquanto essa ficou na fila), guarda pra revisão
    manual em vez de simplesmente falhar.
    """
    from .models import VendaOfflinePendente

    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    vendas_offline = dados.get("vendas", [])
    resultados = []

    for venda_payload in vendas_offline:
        uuid_offline = venda_payload.get("uuid_offline")
        if not uuid_offline:
            resultados.append({"uuid_offline": None, "ok": False, "erro": "Sem identificador único."})
            continue

        if Venda.objects.filter(uuid_offline=uuid_offline).exists():
            resultados.append({"uuid_offline": uuid_offline, "ok": True, "ja_processada": True})
            continue

        if VendaOfflinePendente.objects.filter(uuid_offline=uuid_offline, resolvida=False).exists():
            resultados.append({"uuid_offline": uuid_offline, "ok": False, "erro": "Já está pendente de revisão manual."})
            continue

        try:
            venda = _processar_venda_payload(venda_payload, request.user, uuid_offline=uuid_offline)
            from auditoria.models import registrar
            registrar(
                request.user, "venda_fechada",
                f"Venda #{venda.id} — R$ {venda.total} (sincronizada do modo offline)", request=request,
            )
            resultados.append({"uuid_offline": uuid_offline, "ok": True, "venda_id": venda.id})
        except (EstoqueInsuficienteError, PontosInsuficientesError, CupomInvalidoError, ValeInvalidoError, ValueError, Produto.DoesNotExist, KeyError, TypeError) as exc:
            VendaOfflinePendente.objects.create(
                uuid_offline=uuid_offline, payload_json=json.dumps(venda_payload), erro=str(exc),
            )
            resultados.append({"uuid_offline": uuid_offline, "ok": False, "erro": str(exc), "pendente_revisao": True})

    return JsonResponse({"ok": True, "resultados": resultados})
