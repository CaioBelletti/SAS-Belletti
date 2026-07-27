from decimal import Decimal, InvalidOperation

from auditoria.models import registrar
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .models import CaixaSessao, CategoriaFinanceira, ContaBancaria, ExtratoBancario, MovimentoCaixa
from .services import (
    CaixaJaAbertoError,
    abrir_caixa,
    conciliar_automatico,
    conciliar_manualmente,
    fechar_caixa,
    gerar_parcelas_conta_pagar,
    gerar_parcelas_conta_receber,
    get_sessao_aberta,
    importar_extrato_ofx,
    registrar_sangria,
    registrar_suprimento,
)


@login_required
def bancos(request):
    if request.method == "POST" and request.POST.get("acao") == "criar_conta":
        nome = request.POST.get("nome", "").strip()
        if not nome:
            messages.error(request, "Informe um nome pra conta.")
            return redirect("financeiro:bancos")
        ContaBancaria.objects.create(
            nome=nome,
            banco=request.POST.get("banco", "").strip(),
            agencia=request.POST.get("agencia", "").strip(),
            numero_conta=request.POST.get("numero_conta", "").strip(),
            saldo_inicial=Decimal(request.POST.get("saldo_inicial", "0").replace(",", ".") or "0"),
        )
        messages.success(request, "Conta bancária criada.")
        return redirect("financeiro:bancos")

    return render(request, "financeiro/bancos.html", {
        "contas": ContaBancaria.objects.filter(ativa=True),
    })


@login_required
def extrato_bancario(request, conta_id):
    conta = ContaBancaria.objects.filter(pk=conta_id).first()
    if not conta:
        messages.error(request, "Conta bancária não encontrada.")
        return redirect("financeiro:bancos")

    movimentos = conta.movimentos.order_by("-data", "-criado_em")[:100]
    return render(request, "financeiro/extrato.html", {"conta": conta, "movimentos": movimentos})


@login_required
def importar_ofx(request, conta_id):
    conta = ContaBancaria.objects.filter(pk=conta_id).first()
    if not conta:
        messages.error(request, "Conta bancária não encontrada.")
        return redirect("financeiro:bancos")

    if request.method == "POST":
        arquivo = request.FILES.get("arquivo")
        if not arquivo:
            messages.error(request, "Selecione um arquivo .ofx.")
            return redirect("financeiro:importar_ofx", conta_id=conta.id)
        try:
            conteudo = arquivo.read().decode("utf-8", errors="ignore")
            qtd = importar_extrato_ofx(conta, conteudo)
            messages.success(request, f"{qtd} transação(ões) importada(s) do extrato.")
        except Exception:
            messages.error(request, "Não consegui ler esse arquivo. Confira se é um OFX válido.")
        return redirect("financeiro:conciliar", conta_id=conta.id)

    return render(request, "financeiro/importar_ofx.html", {"conta": conta})


@login_required
def conciliar(request, conta_id):
    conta = ContaBancaria.objects.filter(pk=conta_id).first()
    if not conta:
        messages.error(request, "Conta bancária não encontrada.")
        return redirect("financeiro:bancos")

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "auto":
            qtd = conciliar_automatico(conta)
            messages.success(request, f"{qtd} transação(ões) conciliada(s) automaticamente.")
        elif acao == "vincular_manual":
            extrato = ExtratoBancario.objects.filter(pk=request.POST.get("linha_id")).first()
            movimento = MovimentoCaixa.objects.filter(pk=request.POST.get("movimento_id")).first()
            if extrato and movimento:
                conciliar_manualmente(extrato, movimento)
                movimento.conta_bancaria = conta
                movimento.save(update_fields=["conta_bancaria"])
                messages.success(request, "Vinculado manualmente.")
        return redirect("financeiro:conciliar", conta_id=conta.id)

    linhas_pendentes = conta.extratos.filter(conciliado=False).order_by("-data")
    movimentos_pendentes = MovimentoCaixa.objects.filter(
        conta_bancaria=conta, conciliado=False
    ).order_by("-data")
    linhas_conciliadas = conta.extratos.filter(conciliado=True).order_by("-data")[:20]

    return render(request, "financeiro/conciliar.html", {
        "conta": conta,
        "linhas_pendentes": linhas_pendentes,
        "movimentos_pendentes": movimentos_pendentes,
        "linhas_conciliadas": linhas_conciliadas,
    })


@login_required
def lancar_parcelado(request):
    if request.method == "POST":
        tipo = request.POST.get("tipo")
        descricao = request.POST.get("descricao", "").strip()
        categoria_id = request.POST.get("categoria")
        fornecedor = request.POST.get("fornecedor", "").strip()
        meio_pagamento = request.POST.get("meio_pagamento", "")

        try:
            valor_total = Decimal(request.POST.get("valor_total", "0").replace(",", "."))
            numero_parcelas = int(request.POST.get("numero_parcelas", "1"))
            vencimento_inicial = request.POST.get("vencimento_inicial")
        except (InvalidOperation, ValueError):
            messages.error(request, "Valor ou número de parcelas inválido.")
            return redirect("financeiro:lancar_parcelado")

        if not descricao or not categoria_id or valor_total <= 0 or numero_parcelas < 1 or not vencimento_inicial:
            messages.error(request, "Preencha todos os campos obrigatórios.")
            return redirect("financeiro:lancar_parcelado")

        from datetime import date
        vencimento_inicial = date.fromisoformat(vencimento_inicial)
        categoria = CategoriaFinanceira.objects.filter(pk=categoria_id).first()

        if tipo == "pagar":
            criadas = gerar_parcelas_conta_pagar(
                descricao=descricao, categoria=categoria, valor_total=valor_total,
                vencimento_inicial=vencimento_inicial, numero_parcelas=numero_parcelas,
                fornecedor=fornecedor, meio_pagamento=meio_pagamento,
            )
        else:
            criadas = gerar_parcelas_conta_receber(
                descricao=descricao, categoria=categoria, valor_total=valor_total,
                vencimento_inicial=vencimento_inicial, numero_parcelas=numero_parcelas,
                meio_pagamento=meio_pagamento,
            )

        messages.success(request, f"{len(criadas)} parcela(s) lançada(s), de R$ {criadas[0].valor} cada.")
        return redirect("financeiro:lancar_parcelado")

    return render(request, "financeiro/lancar_parcelado.html", {
        "categorias_despesa": CategoriaFinanceira.objects.filter(tipo="despesa").order_by("nome"),
        "categorias_receita": CategoriaFinanceira.objects.filter(tipo="receita").order_by("nome"),
    })


@login_required
def caixa(request):
    sessao = get_sessao_aberta(usuario=request.user)

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "abrir":
            try:
                valor = Decimal(request.POST.get("valor_abertura", "0").replace(",", "."))
                nova_sessao = abrir_caixa(request.user, valor)
                registrar(request.user, "caixa_aberto", f"Caixa #{nova_sessao.pk} aberto com R$ {valor}", request=request)
                messages.success(request, "Caixa aberto.")
            except CaixaJaAbertoError as exc:
                messages.error(request, str(exc))
            except InvalidOperation:
                messages.error(request, "Valor de abertura inválido.")
            return redirect("financeiro:caixa")

        if not sessao:
            messages.error(request, "Nenhum caixa aberto.")
            return redirect("financeiro:caixa")

        if acao == "sangria":
            try:
                valor = Decimal(request.POST.get("valor", "0").replace(",", "."))
                if valor <= 0:
                    raise InvalidOperation
                registrar_sangria(sessao, valor, request.POST.get("descricao", ""))
                registrar(request.user, "sangria", f"Caixa #{sessao.pk} — sangria de R$ {valor}", request=request)
                messages.success(request, "Sangria registrada.")
            except InvalidOperation:
                messages.error(request, "Valor inválido.")
            return redirect("financeiro:caixa")

        if acao == "suprimento":
            try:
                valor = Decimal(request.POST.get("valor", "0").replace(",", "."))
                if valor <= 0:
                    raise InvalidOperation
                registrar_suprimento(sessao, valor, request.POST.get("descricao", ""))
                registrar(request.user, "suprimento", f"Caixa #{sessao.pk} — suprimento de R$ {valor}", request=request)
                messages.success(request, "Suprimento registrado.")
            except InvalidOperation:
                messages.error(request, "Valor inválido.")
            return redirect("financeiro:caixa")

        if acao == "fechar":
            try:
                valor = Decimal(request.POST.get("valor_fechamento", "0").replace(",", "."))
                fechar_caixa(sessao, valor, request.POST.get("observacoes", ""))
                registrar(request.user, "caixa_fechado", f"Caixa #{sessao.pk} fechado — contado R$ {valor}, diferença R$ {sessao.diferenca}", request=request)

                from notificacoes.models import get_config
                from notificacoes.services import notificar
                config = get_config()
                if abs(sessao.diferenca) > config.limite_diferenca_caixa:
                    notificar(
                        "Diferença grande no fechamento de caixa",
                        f"O caixa #{sessao.pk} (aberto por {sessao.aberta_por}) fechou com "
                        f"diferença de R$ {sessao.diferenca} (esperado R$ {sessao.saldo_esperado}, "
                        f"contado R$ {valor}).",
                    )

                messages.success(request, "Caixa fechado.")
            except InvalidOperation:
                messages.error(request, "Valor de fechamento inválido.")
            return redirect("financeiro:caixa")

    ultimas_sessoes = CaixaSessao.objects.filter(
        fechada_em__isnull=False, aberta_por=request.user
    )[:5]

    return render(request, "financeiro/caixa.html", {
        "sessao": sessao,
        "ultimas_sessoes": ultimas_sessoes,
    })
