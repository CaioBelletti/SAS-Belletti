from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from catalogo.models import Categoria, Produto

from .importacao import ExtracaoNaoSuportadaError, _normalizar_valor, extrair_texto, parse_linhas
from .models import Cotacao, Fornecedor, ItemCotacao, ItemOrdemCompra, OrdemCompra, PropostaCotacao
from .services import NadaRecebidoError, OrdemJaRecebidaError, conferir_recebimento


@login_required
def conferencia_recebimento(request):
    ordens_pendentes = (
        OrdemCompra.objects.filter(status__in=["aberta", "parcial"])
        .select_related("fornecedor")
        .order_by("-criada_em")
    )

    ordem_selecionada = None
    ordem_id = request.GET.get("ordem") or request.POST.get("ordem_id")
    if ordem_id:
        ordem_selecionada = ordens_pendentes.filter(pk=ordem_id).first()

    if request.method == "POST" and ordem_selecionada:
        recebimentos = {}
        for item in ordem_selecionada.itens.all():
            valor = request.POST.get(f"recebido_{item.id}")
            if valor is not None and valor.strip() != "":
                recebimentos[str(item.id)] = valor
        try:
            conferir_recebimento(ordem_selecionada, recebimentos)
            from auditoria.models import registrar
            registrar(request.user, "ordem_recebida", f"Conferência da ordem #{ordem_selecionada.pk}", request=request)
            messages.success(request, "Recebimento registrado. Estoque e financeiro atualizados.")
        except (OrdemJaRecebidaError, NadaRecebidoError, ValueError) as exc:
            messages.error(request, str(exc))
        return redirect("suprimentos:conferencia")

    return render(request, "suprimentos/conferencia.html", {
        "ordens_pendentes": ordens_pendentes,
        "ordem": ordem_selecionada,
    })


@login_required
def cotacoes(request):
    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar_cotacao":
            produtos_ids = request.POST.getlist("produto_id")
            quantidades = request.POST.getlist("quantidade")
            cotacao = Cotacao.objects.create(observacoes=request.POST.get("observacoes", ""))
            criados = 0
            for pid, qtd in zip(produtos_ids, quantidades):
                if not pid:
                    continue
                try:
                    qtd_int = max(int(qtd), 1)
                except (ValueError, TypeError):
                    qtd_int = 1
                ItemCotacao.objects.create(cotacao=cotacao, produto_id=pid, quantidade=qtd_int)
                criados += 1
            if not criados:
                cotacao.delete()
                messages.error(request, "Selecione ao menos um produto.")
            else:
                messages.success(request, f"Cotação #{cotacao.pk} criada com {criados} item(ns).")
            return redirect("suprimentos:cotacoes")

        if acao == "adicionar_proposta":
            item_cotacao = get_object_or_404(ItemCotacao, pk=request.POST.get("item_cotacao_id"))
            fornecedor_id = request.POST.get("fornecedor_id")
            try:
                preco = Decimal(str(request.POST.get("preco_unitario", "0")).replace(",", "."))
            except InvalidOperation:
                messages.error(request, "Preço inválido.")
                return redirect(f"/suprimentos/cotacoes/?cotacao={item_cotacao.cotacao_id}")
            prazo = request.POST.get("prazo_dias") or None

            PropostaCotacao.objects.update_or_create(
                item_cotacao=item_cotacao, fornecedor_id=fornecedor_id,
                defaults={"preco_unitario": preco, "prazo_dias": prazo},
            )
            messages.success(request, "Proposta registrada.")
            return redirect(f"/suprimentos/cotacoes/?cotacao={item_cotacao.cotacao_id}")

        if acao == "gerar_ordens":
            cotacao = get_object_or_404(Cotacao, pk=request.POST.get("cotacao_id"))
            escolhas = {}
            for item in cotacao.itens.all():
                proposta_id = request.POST.get(f"escolha_{item.id}")
                if proposta_id:
                    escolhas[item.id] = PropostaCotacao.objects.filter(pk=proposta_id).first()

            if not escolhas:
                messages.error(request, "Escolha ao menos uma proposta vencedora.")
                return redirect(f"/suprimentos/cotacoes/?cotacao={cotacao.pk}")

            ordens_por_fornecedor = {}
            for item_id, proposta in escolhas.items():
                if not proposta:
                    continue
                item = ItemCotacao.objects.get(pk=item_id)
                fornecedor = proposta.fornecedor
                if fornecedor.id not in ordens_por_fornecedor:
                    ordens_por_fornecedor[fornecedor.id] = OrdemCompra.objects.create(fornecedor=fornecedor)
                ordem = ordens_por_fornecedor[fornecedor.id]
                ItemOrdemCompra.objects.create(
                    ordem=ordem, produto=item.produto, quantidade=item.quantidade,
                    preco_unitario=proposta.preco_unitario,
                )

            cotacao.status = "finalizada"
            cotacao.save(update_fields=["status"])

            from aprovacoes.services import verificar_aprovacao_compra
            for ordem in ordens_por_fornecedor.values():
                verificar_aprovacao_compra(ordem)

            messages.success(
                request,
                f"{len(ordens_por_fornecedor)} ordem(ns) de compra gerada(s) a partir da cotação.",
            )
            return redirect("suprimentos:cotacoes")

    cotacao_id = request.GET.get("cotacao")
    cotacao_aberta = None
    if cotacao_id:
        cotacao_aberta = Cotacao.objects.filter(pk=cotacao_id).prefetch_related(
            "itens__produto", "itens__propostas__fornecedor"
        ).first()

    return render(request, "suprimentos/cotacoes.html", {
        "cotacoes_todas": Cotacao.objects.order_by("-criada_em")[:20],
        "cotacao": cotacao_aberta,
        "produtos": Produto.objects.filter(ativo=True).order_by("nome"),
        "fornecedores": Fornecedor.objects.order_by("nome"),
    })


@login_required
def analise_compras(request):
    from django.db.models import Avg, Count, F, Min, Sum

    preco_medio_produtos = (
        ItemOrdemCompra.objects.filter(quantidade_recebida__gt=0)
        .values("produto__nome", "produto__sku")
        .annotate(
            preco_medio=Avg("preco_unitario"),
            menor_preco=Min("preco_unitario"),
            qtd_total=Sum("quantidade_recebida"),
        )
        .order_by("produto__nome")
    )

    ranking_fornecedores = (
        OrdemCompra.objects.filter(status__in=["recebida", "parcial"])
        .values("fornecedor__nome")
        .annotate(
            total_ordens=Count("id", distinct=True),
            valor_total=Sum(F("itens__quantidade_recebida") * F("itens__preco_unitario")),
        )
        .order_by("-valor_total")
    )

    ordens_com_recebimento = OrdemCompra.objects.filter(recebida_em__isnull=False).select_related("fornecedor")
    prazo_entrega_por_fornecedor = {}
    for ordem in ordens_com_recebimento:
        prazo_entrega_por_fornecedor.setdefault(ordem.fornecedor.nome, []).append(ordem.dias_ate_recebimento)

    ordens_com_prazo = OrdemCompra.objects.filter(
        recebida_em__isnull=False, data_prevista__isnull=False
    ).select_related("fornecedor")
    prazo_por_fornecedor = {}
    for ordem in ordens_com_prazo:
        prazo_por_fornecedor.setdefault(ordem.fornecedor.nome, []).append(ordem.atraso_dias)

    avaliacoes_por_fornecedor = dict(Fornecedor.objects.values_list("nome", "avaliacao"))

    ranking = []
    for r in ranking_fornecedores:
        atrasos = prazo_por_fornecedor.get(r["fornecedor__nome"], [])
        atraso_medio = round(sum(atrasos) / len(atrasos), 1) if atrasos else None
        prazos_entrega = prazo_entrega_por_fornecedor.get(r["fornecedor__nome"], [])
        prazo_medio = round(sum(prazos_entrega) / len(prazos_entrega), 1) if prazos_entrega else None
        ranking.append({
            "fornecedor": r["fornecedor__nome"],
            "total_ordens": r["total_ordens"],
            "valor_total": r["valor_total"] or 0,
            "atraso_medio": atraso_medio,
            "prazo_medio": prazo_medio,
            "avaliacao": avaliacoes_por_fornecedor.get(r["fornecedor__nome"]),
        })

    return render(request, "suprimentos/analise.html", {
        "preco_medio_produtos": preco_medio_produtos,
        "ranking_fornecedores": ranking,
    })


@login_required
def importar_upload(request):
    fornecedores = Fornecedor.objects.order_by("nome")
    categorias = Categoria.objects.order_by("nome")

    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        fornecedor_id = request.POST.get("fornecedor")
        categoria_id = request.POST.get("categoria")

        if not arquivo:
            messages.error(request, "Selecione um arquivo (print, PDF ou .txt).")
            return redirect("suprimentos:importar_upload")
        if not fornecedor_id:
            messages.error(request, "Selecione o fornecedor.")
            return redirect("suprimentos:importar_upload")
        if not categoria_id:
            messages.error(request, "Selecione a categoria dos produtos.")
            return redirect("suprimentos:importar_upload")

        try:
            texto = extrair_texto(arquivo)
        except ExtracaoNaoSuportadaError as exc:
            messages.error(request, str(exc))
            return redirect("suprimentos:importar_upload")
        except Exception:
            messages.error(request, "Não consegui ler esse arquivo. Tente outro formato.")
            return redirect("suprimentos:importar_upload")

        itens = parse_linhas(texto)
        if not itens:
            messages.error(
                request,
                "Não encontrei nenhuma linha com nome + valor nesse arquivo. "
                "Confira se o texto está legível e tente novamente.",
            )
            return redirect("suprimentos:importar_upload")

        return render(request, "suprimentos/importar_preview.html", {
            "itens": itens,
            "fornecedor_id": fornecedor_id,
            "categoria_id": categoria_id,
        })

    return render(request, "suprimentos/importar_upload.html", {
        "fornecedores": fornecedores,
        "categorias": categorias,
    })


def _gerar_sku_unico(nome):
    base = "".join(ch for ch in nome.upper() if ch.isalnum())[:12] or "PROD"
    candidato = base
    sufixo = 1
    while Produto.objects.filter(sku=candidato).exists():
        sufixo += 1
        candidato = f"{base}-{sufixo}"
    return candidato


@login_required
def importar_confirmar(request):
    if request.method != "POST":
        return redirect("suprimentos:importar_upload")

    fornecedor_id = request.POST.get("fornecedor_id")
    categoria_id = request.POST.get("categoria_id")
    nomes = request.POST.getlist("nome")
    quantidades = request.POST.getlist("quantidade")
    valores = request.POST.getlist("valor_total")

    try:
        fornecedor = Fornecedor.objects.get(pk=fornecedor_id)
        categoria = Categoria.objects.get(pk=categoria_id)
    except (Fornecedor.DoesNotExist, Categoria.DoesNotExist):
        messages.error(request, "Fornecedor ou categoria inválidos.")
        return redirect("suprimentos:importar_upload")

    ordem = OrdemCompra.objects.create(fornecedor=fornecedor)
    criados, aproveitados = 0, 0

    for nome, qtd_str, valor_str in zip(nomes, quantidades, valores):
        nome = nome.strip()
        if not nome:
            continue
        try:
            quantidade = max(int(qtd_str), 1)
        except (ValueError, TypeError):
            quantidade = 1
        try:
            valor_total = _normalizar_valor(valor_str)
        except (InvalidOperation, TypeError):
            continue
        if valor_total <= 0:
            continue

        preco_unitario = (valor_total / quantidade).quantize(Decimal("0.01"))

        produto = Produto.objects.filter(nome__iexact=nome).first()
        if produto:
            aproveitados += 1
        else:
            produto = Produto.objects.create(
                sku=_gerar_sku_unico(nome),
                nome=nome,
                categoria=categoria,
                preco_custo=preco_unitario,
                preco_venda=preco_unitario,
            )
            criados += 1

        ItemOrdemCompra.objects.create(
            ordem=ordem, produto=produto, quantidade=quantidade, preco_unitario=preco_unitario,
        )

    if not ordem.itens.exists():
        ordem.delete()
        messages.error(request, "Nenhum item válido pra importar.")
        return redirect("suprimentos:importar_upload")

    from aprovacoes.services import verificar_aprovacao_compra
    verificar_aprovacao_compra(ordem)

    messages.success(
        request,
        f"Ordem de compra #{ordem.pk} criada com {ordem.itens.count()} itens "
        f"({criados} produtos novos, {aproveitados} já existentes). "
        f"Revise e clique em 'Receber' quando estiver tudo certo.",
    )
    return redirect(f"/admin/suprimentos/ordemcompra/{ordem.pk}/change/")
