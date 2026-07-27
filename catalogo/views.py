import io

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import F
from django.shortcuts import redirect, render

from .models import Categoria, Produto


def _gerar_codigo_interno(produto):
    return f"BEL{produto.id:08d}"


def _svg_barcode(codigo):
    import barcode
    from barcode.writer import SVGWriter

    code128 = barcode.get("code128", codigo, writer=SVGWriter())
    buffer = io.BytesIO()
    code128.write(buffer, options={
        "module_height": 9.0, "font_size": 8, "text_distance": 2, "quiet_zone": 2,
    })
    return buffer.getvalue().decode("utf-8")


@login_required
def reservas(request):
    from .models import Reserva
    from vendas.models import Cliente

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar":
            produto_id = request.POST.get("produto_id")
            cliente_id = request.POST.get("cliente_id") or None
            validade = request.POST.get("validade") or None
            observacoes = request.POST.get("observacoes", "").strip()
            try:
                quantidade = int(request.POST.get("quantidade", "0"))
            except ValueError:
                quantidade = 0

            produto = Produto.objects.filter(pk=produto_id).first()
            if not produto or quantidade <= 0:
                messages.error(request, "Selecione um produto e uma quantidade válida.")
                return redirect("catalogo:reservas")
            if produto.estoque_disponivel < quantidade:
                messages.error(
                    request,
                    f"{produto.nome} só tem {produto.estoque_disponivel} unidade(s) disponível(is) "
                    f"pra reservar (estoque total {produto.estoque_atual}, já reservado {produto.estoque_reservado}).",
                )
                return redirect("catalogo:reservas")

            Reserva.objects.create(
                produto=produto, cliente_id=cliente_id, quantidade=quantidade,
                validade=validade, observacoes=observacoes, criada_por=request.user,
            )
            messages.success(request, f"Reserva de {quantidade}x {produto.nome} criada.")
            return redirect("catalogo:reservas")

        reserva_id = request.POST.get("reserva_id")
        reserva = Reserva.objects.filter(pk=reserva_id).first()
        if reserva:
            if acao == "cancelar":
                reserva.status = "cancelada"
                reserva.save(update_fields=["status"])
                messages.success(request, "Reserva cancelada.")
            elif acao == "atender":
                reserva.status = "atendida"
                reserva.save(update_fields=["status"])
                messages.success(request, "Reserva marcada como atendida.")
        return redirect("catalogo:reservas")

    reservas_ativas = (
        Reserva.objects.filter(status="ativa")
        .select_related("produto", "cliente")
        .order_by("validade", "-criada_em")
    )
    reservas_historico = (
        Reserva.objects.exclude(status="ativa")
        .select_related("produto", "cliente")
        .order_by("-atualizada_em")[:15]
    )

    return render(request, "catalogo/reservas.html", {
        "reservas_ativas": reservas_ativas,
        "reservas_historico": reservas_historico,
        "produtos": Produto.objects.filter(ativo=True).order_by("nome"),
        "clientes": Cliente.objects.order_by("nome"),
    })


@login_required
def perdas(request):
    from datetime import timedelta

    from django.db.models import Sum
    from django.utils import timezone

    from .models import MovimentacaoEstoque

    if request.method == "POST":
        produto_id = request.POST.get("produto_id")
        categoria = request.POST.get("categoria")
        observacao = request.POST.get("observacao", "").strip()
        try:
            quantidade = int(request.POST.get("quantidade", "0"))
        except ValueError:
            quantidade = 0

        produto = Produto.objects.filter(pk=produto_id).first()
        if not produto or quantidade <= 0 or not categoria:
            messages.error(request, "Selecione o produto, categoria e uma quantidade válida.")
            return redirect("catalogo:perdas")
        if produto.estoque_atual < quantidade:
            messages.error(
                request,
                f"Estoque de {produto.nome} é {produto.estoque_atual}, não dá pra baixar {quantidade}.",
            )
            return redirect("catalogo:perdas")

        MovimentacaoEstoque.objects.create(
            produto=produto, tipo="saida", categoria=categoria, quantidade=quantidade,
            motivo=observacao or dict(MovimentacaoEstoque.CATEGORIA_CHOICES).get(categoria, ""),
        )
        messages.success(request, f"Baixa registrada: {quantidade}x {produto.nome}.")
        return redirect("catalogo:perdas")

    hoje = timezone.localdate()
    inicio_mes = hoje.replace(day=1)
    resumo = (
        MovimentacaoEstoque.objects.filter(
            tipo="saida", categoria__in=[c[0] for c in MovimentacaoEstoque.CATEGORIA_CHOICES if c[0]],
            criado_em__date__gte=inicio_mes,
        )
        .values("categoria")
        .annotate(
            quantidade_total=Sum("quantidade"),
            valor_total=Sum(F("quantidade") * F("produto__preco_custo")),
        )
        .order_by("-valor_total")
    )
    categorias_dict = dict(MovimentacaoEstoque.CATEGORIA_CHOICES)
    resumo = [
        {"categoria": categorias_dict.get(r["categoria"], r["categoria"]),
         "quantidade_total": r["quantidade_total"], "valor_total": r["valor_total"] or 0}
        for r in resumo
    ]

    ultimas = (
        MovimentacaoEstoque.objects.filter(
            tipo="saida", categoria__in=[c[0] for c in MovimentacaoEstoque.CATEGORIA_CHOICES if c[0]],
        )
        .select_related("produto")
        .order_by("-criado_em")[:15]
    )

    return render(request, "catalogo/perdas.html", {
        "produtos": Produto.objects.filter(ativo=True).order_by("nome"),
        "categorias_perda": [c for c in MovimentacaoEstoque.CATEGORIA_CHOICES if c[0]],
        "resumo": resumo,
        "ultimas": ultimas,
    })


@login_required
def inventario(request):
    from .models import Categoria, InventarioSessao
    from .services import abrir_inventario, finalizar_inventario, registrar_contagem

    sessao_aberta = InventarioSessao.objects.filter(fechada_em__isnull=True).first()

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "abrir":
            categoria_id = request.POST.get("categoria") or None
            categoria = Categoria.objects.filter(pk=categoria_id).first() if categoria_id else None
            try:
                abrir_inventario(request.user, categoria=categoria)
                messages.success(request, "Inventário aberto. Já dá pra começar a contar.")
            except ValueError as exc:
                messages.error(request, str(exc))
            return redirect("catalogo:inventario")

        if not sessao_aberta:
            messages.error(request, "Nenhum inventário aberto.")
            return redirect("catalogo:inventario")

        if acao == "salvar_contagem":
            for item in sessao_aberta.itens.all():
                valor = request.POST.get(f"contagem_{item.id}")
                if valor is not None and valor.strip() != "":
                    try:
                        registrar_contagem(item, int(valor))
                    except ValueError:
                        pass
            messages.success(request, "Contagem salva.")
            return redirect("catalogo:inventario")

        if acao == "finalizar":
            _, ajustados = finalizar_inventario(sessao_aberta)
            messages.success(
                request,
                f"Inventário finalizado — {ajustados} produto(s) tiveram o estoque ajustado.",
            )
            return redirect("catalogo:inventario")

    itens = sessao_aberta.itens.select_related("produto").order_by("produto__nome") if sessao_aberta else []
    ultimas_sessoes = InventarioSessao.objects.filter(fechada_em__isnull=False)[:5]

    return render(request, "catalogo/inventario.html", {
        "sessao": sessao_aberta,
        "itens": itens,
        "categorias": Categoria.objects.order_by("nome"),
        "ultimas_sessoes": ultimas_sessoes,
    })


@login_required
def consulta_carta(request):
    from .imagens_api import buscar_candidatos_imagem

    jogo = request.GET.get("jogo", "")
    termo = request.GET.get("termo", "")
    resultados = []
    if jogo and termo:
        resultados = buscar_candidatos_imagem(termo, jogo)

    return render(request, "catalogo/consulta_carta.html", {
        "jogo": jogo, "termo": termo, "resultados": resultados,
    })


@login_required
def buscar_imagem_produto(request, produto_id):
    from django.core.files.base import ContentFile

    from .imagens_api import baixar_imagem, buscar_candidatos_imagem, buscar_por_codigo_barras

    produto = Produto.objects.select_related("categoria").get(pk=produto_id)
    jogo = produto.categoria.jogo_tcg if produto.categoria else ""
    eh_produto_lacrado = produto.tipo_composicao != "simples"

    if request.method == "POST":
        imagem_url = request.POST.get("imagem_url")
        if not imagem_url:
            messages.error(request, "Selecione uma imagem antes de confirmar.")
            return redirect("catalogo:buscar_imagem_produto", produto_id=produto.id)

        conteudo = baixar_imagem(imagem_url)
        if not conteudo:
            messages.error(request, "Não consegui baixar essa imagem — tente outra ou envie manualmente.")
            return redirect("catalogo:buscar_imagem_produto", produto_id=produto.id)

        nome_arquivo = f"{produto.sku or produto.id}.jpg"
        produto.imagem.save(nome_arquivo, ContentFile(conteudo), save=True)
        messages.success(request, f"Imagem de {produto.nome} atualizada.")
        return redirect(f"/admin/catalogo/produto/{produto.id}/change/")

    # Produto lacrado (booster box, blister, ETB, case, etc) busca por
    # código de barras por padrão — não existe "banco de dados de
    # cartas" pra embalagem, mas o código de barras é exato.
    # Carta avulsa busca pelo nome no banco de dados do jogo certo.
    modo = request.GET.get("modo") or ("codigo_barras" if eh_produto_lacrado or not jogo else "nome")

    candidatos = []
    termo_busca = request.GET.get("termo", produto.nome)
    codigo_busca = request.GET.get("codigo", produto.ean or produto.codigo_barras or "")

    if modo == "nome" and jogo:
        candidatos = buscar_candidatos_imagem(termo_busca, jogo)
    elif modo == "codigo_barras":
        candidatos = buscar_por_codigo_barras(codigo_busca)

    return render(request, "catalogo/buscar_imagem.html", {
        "produto": produto,
        "jogo": jogo,
        "modo": modo,
        "termo_busca": termo_busca,
        "codigo_busca": codigo_busca,
        "candidatos": candidatos,
    })


@login_required
def composicao(request):
    produtos_compostos = Produto.objects.filter(ativo=True, componentes_kit__isnull=False).distinct()

    if request.method == "POST":
        from .services import (
            EstoqueInsuficienteComposicaoError,
            SemComponentesError,
            desmontar_composto,
            montar_composto,
        )

        produto_id = request.POST.get("produto_id")
        acao = request.POST.get("acao")
        try:
            quantidade = int(request.POST.get("quantidade", "0"))
        except ValueError:
            quantidade = 0

        produto = Produto.objects.filter(pk=produto_id).first()
        if not produto or quantidade <= 0:
            messages.error(request, "Selecione um produto e uma quantidade válida.")
            return redirect("catalogo:composicao")

        try:
            if acao == "desmontar":
                desmontar_composto(produto, quantidade)
                messages.success(request, f"{quantidade}x {produto.nome} desmontado(s) em componentes.")
            elif acao == "montar":
                montar_composto(produto, quantidade)
                messages.success(request, f"{quantidade}x {produto.nome} montado(s) a partir dos componentes.")
        except (SemComponentesError, EstoqueInsuficienteComposicaoError) as exc:
            messages.error(request, str(exc))
        return redirect("catalogo:composicao")

    return render(request, "catalogo/composicao.html", {"produtos_compostos": produtos_compostos})


@login_required
def etiquetas(request):
    categoria_id = request.GET.get("categoria")
    apenas_sem_codigo = request.GET.get("apenas_sem_codigo") == "1"

    produtos_qs = Produto.objects.filter(ativo=True)
    if categoria_id:
        produtos_qs = produtos_qs.filter(categoria_id=categoria_id)
    if apenas_sem_codigo:
        produtos_qs = produtos_qs.filter(codigo_barras__isnull=True) | produtos_qs.filter(codigo_barras="")

    selecionados_ids = request.GET.getlist("produto_id")

    etiquetas_geradas = []
    if selecionados_ids:
        produtos = Produto.objects.filter(id__in=selecionados_ids)
        for produto in produtos:
            if not produto.codigo_barras:
                produto.codigo_barras = _gerar_codigo_interno(produto)
                produto.save(update_fields=["codigo_barras"])
            etiquetas_geradas.append({
                "produto": produto,
                "svg": _svg_barcode(produto.codigo_barras),
            })

    return render(request, "catalogo/etiquetas.html", {
        "produtos": produtos_qs.order_by("nome"),
        "categorias": Categoria.objects.order_by("nome"),
        "etiquetas_geradas": etiquetas_geradas,
        "categoria_selecionada": categoria_id,
        "apenas_sem_codigo": apenas_sem_codigo,
    })
