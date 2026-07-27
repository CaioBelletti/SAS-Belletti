from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

FORMAS_A_VISTA = {"dinheiro", "pix", "debito", "credito_avista", "vale"}


def anonimizar_cliente(cliente):
    """
    Direito ao esquecimento (LGPD): apaga os dados pessoais do
    cliente, mas MANTÉM o histórico de vendas (obrigação fiscal/
    contábil de retenção não é a mesma coisa que dado pessoal — o
    valor e a data da venda continuam, só a identidade é removida).
    """
    cliente.nome = f"Cliente removido #{cliente.pk}"
    cliente.telefone = ""
    cliente.email = ""
    cliente.documento = ""
    cliente.data_nascimento = None
    cliente.cep = ""
    cliente.logradouro = ""
    cliente.numero = ""
    cliente.complemento = ""
    cliente.bairro = ""
    cliente.cidade = ""
    cliente.uf = ""
    cliente.consentimento_dados = False
    cliente.anonimizado = True
    cliente.save()
    return cliente


class VendaJaFechadaError(Exception):
    pass


class EstoqueInsuficienteError(Exception):
    pass


class DevolucaoJaProcessadaError(Exception):
    pass


class QuantidadeDevolucaoInvalidaError(Exception):
    pass


class PontosInsuficientesError(Exception):
    pass


class CupomInvalidoError(Exception):
    pass


class ValeInvalidoError(Exception):
    pass


@transaction.atomic
def processar_devolucao(devolucao):
    """
    Processa a devolução: valida se as quantidades pedidas não
    excedem o que foi vendido (descontando devoluções anteriores),
    devolve o estoque, e estorna o valor no financeiro:
    - se a conta a receber da venda já estava "recebida" (à vista),
      lança uma saída no caixa (o dinheiro sai de fato)
    - se ainda estava "pendente" (parcelado), reduz o valor da conta
      a receber (ou cancela, se a devolução cobrir o valor todo)
    """
    from catalogo.models import MovimentacaoEstoque
    from financeiro.models import ContaReceber, MovimentoCaixa
    from financeiro.services import get_sessao_aberta

    if devolucao.processada:
        raise DevolucaoJaProcessadaError("Essa devolução já foi processada.")

    itens = list(devolucao.itens.select_related("produto"))
    if not itens:
        raise ValueError("Não é possível processar uma devolução sem itens.")

    venda = devolucao.venda
    itens_venda_por_produto = {item.produto_id: item for item in venda.itens.all()}

    for item in itens:
        item_venda = itens_venda_por_produto.get(item.produto_id)
        if item_venda is None:
            raise QuantidadeDevolucaoInvalidaError(
                f"O produto {item.produto.sku} não faz parte desta venda."
            )
        if item.quantidade > item_venda.quantidade_disponivel_devolucao:
            raise QuantidadeDevolucaoInvalidaError(
                f"Só é possível devolver até {item_venda.quantidade_disponivel_devolucao}x "
                f"de {item.produto.sku} (já vendido/devolvido considerado)."
            )

    for item in itens:
        MovimentacaoEstoque.objects.create(
            produto=item.produto,
            tipo="entrada",
            quantidade=item.quantidade,
            motivo=f"Devolução #{devolucao.pk} da venda #{venda.pk}",
            venda=venda,
        )

    total_devolvido = devolucao.total
    conta = ContaReceber.objects.filter(venda=venda).first()
    hoje = timezone.localdate()

    if conta and conta.status == "recebido":
        MovimentoCaixa.objects.create(
            tipo="saida",
            valor=total_devolvido,
            descricao=f"Estorno devolução #{devolucao.pk} (venda #{venda.pk})",
            data=hoje,
            conta_receber=conta,
            sessao=get_sessao_aberta(usuario=venda.vendedor),
        )
    elif conta and conta.status == "pendente":
        novo_valor = conta.valor - total_devolvido
        if novo_valor <= 0:
            conta.valor = Decimal("0")
            conta.status = "cancelado"
        else:
            conta.valor = novo_valor
        conta.save(update_fields=["valor", "status"])

    devolucao.processada = True
    devolucao.processada_em = timezone.now()
    devolucao.save(update_fields=["processada", "processada_em"])

    if venda.cliente:
        from .models import get_config_fidelidade
        config = get_config_fidelidade()
        if config.ativo and config.valor_por_ponto > 0:
            pontos_a_remover = int(total_devolvido / config.valor_por_ponto)
            cliente = venda.cliente
            cliente.pontos_fidelidade = max(cliente.pontos_fidelidade - pontos_a_remover, 0)
            cliente.save(update_fields=["pontos_fidelidade"])

    return devolucao


@transaction.atomic
def fechar_venda(venda):
    """
    Fecha a venda: valida estoque, baixa o estoque de cada item,
    e cria a(s) conta(s) a receber (já quitada(s), se a forma de
    pagamento for à vista). Tudo dentro de uma transação — se algo
    falhar no meio, nada é salvo.

    Se a venda tiver registros em `pagamentos` (PagamentoVenda), trata
    como pagamento misto: uma conta a receber por forma de pagamento,
    proporcional ao valor de cada uma. Senão, usa o campo único
    `forma_pagamento` da própria venda (fluxo mais simples/antigo).
    """
    from catalogo.models import MovimentacaoEstoque
    from financeiro.models import CategoriaFinanceira, ContaReceber, MovimentoCaixa
    from financeiro.services import get_sessao_aberta

    if venda.status != "aberta":
        raise VendaJaFechadaError("Essa venda já foi fechada ou cancelada.")

    itens = list(venda.itens.select_related("produto"))
    if not itens:
        raise ValueError("Não é possível fechar uma venda sem itens.")

    for item in itens:
        if item.produto.estoque_atual < item.quantidade:
            raise EstoqueInsuficienteError(
                f"Estoque insuficiente de {item.produto.sku} "
                f"(disponível: {item.produto.estoque_atual}, pedido: {item.quantidade})"
            )

    pagamentos = list(venda.pagamentos.all())
    if pagamentos:
        soma_pagamentos = sum((p.valor for p in pagamentos), Decimal("0"))
        if abs(soma_pagamentos - venda.total) > Decimal("0.01"):
            raise ValueError(
                f"A soma dos pagamentos (R$ {soma_pagamentos}) não bate com "
                f"o total da venda (R$ {venda.total})."
            )

    if venda.pontos_resgatados > 0:
        if not venda.cliente:
            raise PontosInsuficientesError("Resgate de pontos exige um cliente identificado.")
        if venda.cliente.pontos_fidelidade < venda.pontos_resgatados:
            raise PontosInsuficientesError(
                f"Cliente tem {venda.cliente.pontos_fidelidade} ponto(s), "
                f"não é possível resgatar {venda.pontos_resgatados}."
            )

    if venda.credito_usado > 0:
        if not venda.cliente:
            raise PontosInsuficientesError("Usar crédito exige um cliente identificado.")
        if venda.cliente.saldo_credito < venda.credito_usado:
            raise PontosInsuficientesError(
                f"Cliente tem R$ {venda.cliente.saldo_credito} de crédito, "
                f"não é possível usar R$ {venda.credito_usado}."
            )

    if venda.cupom and not venda.cupom.valido:
        raise CupomInvalidoError(f"O cupom {venda.cupom.codigo} não é mais válido.")

    for pagamento in pagamentos:
        if pagamento.forma_pagamento == "vale":
            if not pagamento.vale:
                raise ValeInvalidoError("Pagamento em vale precisa informar qual vale foi usado.")
            if not pagamento.vale.valido:
                raise ValeInvalidoError(f"O vale {pagamento.vale.codigo} não tem saldo ou está inativo.")
            if pagamento.vale.saldo < pagamento.valor:
                raise ValeInvalidoError(
                    f"O vale {pagamento.vale.codigo} tem saldo de R$ {pagamento.vale.saldo}, "
                    f"insuficiente pros R$ {pagamento.valor} usados."
                )

    for item in itens:
        MovimentacaoEstoque.objects.create(
            produto=item.produto,
            tipo="saida",
            quantidade=item.quantidade,
            motivo=f"Venda #{venda.pk}",
            venda=venda,
        )

    for pagamento in pagamentos:
        if pagamento.forma_pagamento == "vale" and pagamento.vale:
            from .models import Vale
            Vale.objects.filter(pk=pagamento.vale_id).update(
                saldo=F("saldo") - pagamento.valor
            )

    if venda.cupom:
        from .models import CupomDesconto
        CupomDesconto.objects.filter(pk=venda.cupom_id).update(usos_atuais=F("usos_atuais") + 1)

    categoria_vendas, _ = CategoriaFinanceira.objects.get_or_create(
        nome="Venda de produtos", tipo="receita"
    )
    hoje = timezone.localdate()
    sessao_aberta = get_sessao_aberta(usuario=venda.vendedor)

    if pagamentos:
        for pagamento in pagamentos:
            a_vista = pagamento.forma_pagamento in FORMAS_A_VISTA

            if pagamento.forma_pagamento == "credito_parcelado" and pagamento.parcelas > 1:
                from financeiro.services import gerar_parcelas_conta_receber
                gerar_parcelas_conta_receber(
                    descricao=f"Venda #{venda.pk}",
                    categoria=categoria_vendas,
                    valor_total=pagamento.valor,
                    vencimento_inicial=hoje,
                    numero_parcelas=pagamento.parcelas,
                    cliente=venda.cliente,
                    venda=venda,
                    meio_pagamento="cartao",
                )
                continue

            conta = ContaReceber.objects.create(
                descricao=f"Venda #{venda.pk}",
                cliente=venda.cliente,
                venda=venda,
                categoria=categoria_vendas,
                valor=pagamento.valor,
                vencimento=hoje,
                status="recebido" if a_vista else "pendente",
                data_recebimento=hoje if a_vista else None,
                forma_pagamento=pagamento.get_forma_pagamento_display(),
            )
            if a_vista:
                MovimentoCaixa.objects.create(
                    tipo="entrada",
                    valor=pagamento.valor,
                    descricao=f"Recebimento venda #{venda.pk} ({pagamento.get_forma_pagamento_display()})",
                    data=hoje,
                    conta_receber=conta,
                    sessao=sessao_aberta,
                )
    else:
        a_vista = venda.forma_pagamento in FORMAS_A_VISTA
        conta = ContaReceber.objects.create(
            descricao=f"Venda #{venda.pk}",
            cliente=venda.cliente,
            venda=venda,
            categoria=categoria_vendas,
            valor=venda.total,
            vencimento=hoje,
            status="recebido" if a_vista else "pendente",
            data_recebimento=hoje if a_vista else None,
            forma_pagamento=venda.get_forma_pagamento_display(),
        )
        if a_vista:
            MovimentoCaixa.objects.create(
                tipo="entrada",
                valor=venda.total,
                descricao=f"Recebimento venda #{venda.pk}",
                data=hoje,
                conta_receber=conta,
                sessao=sessao_aberta,
            )

    venda.status = "fechada"
    venda.fechada_em = timezone.now()
    venda.save(update_fields=["status", "fechada_em"])

    if venda.cliente:
        from .models import get_config_fidelidade
        config = get_config_fidelidade()
        cliente = venda.cliente

        if venda.pontos_resgatados > 0:
            cliente.pontos_fidelidade -= venda.pontos_resgatados

        if config.ativo and config.valor_por_ponto > 0:
            pontos_ganhos = int(venda.total / config.valor_por_ponto)
            cliente.pontos_fidelidade += pontos_ganhos

        if venda.credito_usado > 0:
            cliente.saldo_credito -= venda.credito_usado

        if config.percentual_cashback > 0:
            cashback_ganho = (venda.total * config.percentual_cashback / 100).quantize(Decimal("0.01"))
            cliente.saldo_credito += cashback_ganho

        cliente.save(update_fields=["pontos_fidelidade", "saldo_credito"])

    return venda
