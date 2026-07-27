from django.db import transaction
from django.utils import timezone


class CaixaJaAbertoError(Exception):
    pass


class NenhumCaixaAbertoError(Exception):
    pass


def get_sessao_aberta(usuario=None):
    """
    Sem `usuario`: devolve qualquer caixa aberto (usado em fluxos sem
    vendedor identificado, ex: venda criada direto pelo admin).
    Com `usuario`: devolve o caixa aberto DESSE usuário — permite
    múltiplos caixas abertos ao mesmo tempo, um por vendedor/terminal.
    """
    from .models import CaixaSessao

    qs = CaixaSessao.objects.filter(fechada_em__isnull=True)
    if usuario is not None:
        return qs.filter(aberta_por=usuario).first()
    return qs.first()


@transaction.atomic
def abrir_caixa(usuario, valor_abertura):
    from .models import CaixaSessao

    if get_sessao_aberta(usuario=usuario):
        raise CaixaJaAbertoError("Você já tem um caixa aberto. Feche o atual antes de abrir outro.")

    return CaixaSessao.objects.create(aberta_por=usuario, valor_abertura=valor_abertura)


@transaction.atomic
def fechar_caixa(sessao, valor_informado, observacoes=""):
    if not sessao.aberta:
        raise ValueError("Esse caixa já está fechado.")

    sessao.valor_fechamento_informado = valor_informado
    sessao.fechada_em = timezone.now()
    if observacoes:
        sessao.observacoes = observacoes
    sessao.save(update_fields=["valor_fechamento_informado", "fechada_em", "observacoes"])
    return sessao


@transaction.atomic
def registrar_sangria(sessao, valor, descricao):
    from .models import MovimentoCaixa

    if not sessao.aberta:
        raise ValueError("Esse caixa já está fechado.")

    return MovimentoCaixa.objects.create(
        tipo="saida", valor=valor, descricao=f"Sangria — {descricao}" if descricao else "Sangria",
        data=timezone.localdate(), sessao=sessao,
    )


@transaction.atomic
def registrar_suprimento(sessao, valor, descricao):
    from .models import MovimentoCaixa

    if not sessao.aberta:
        raise ValueError("Esse caixa já está fechado.")

    return MovimentoCaixa.objects.create(
        tipo="entrada", valor=valor, descricao=f"Suprimento — {descricao}" if descricao else "Suprimento",
        data=timezone.localdate(), sessao=sessao,
    )


# --- Parcelamento real e recorrência ------------------------------------------

import uuid
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta


def _dividir_valor(valor_total, numero_parcelas):
    """
    Divide um valor em N parcelas iguais, jogando a diferença de
    arredondamento na última parcela (pra soma bater exatamente).
    """
    parcela = (valor_total / numero_parcelas).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    valores = [parcela] * numero_parcelas
    diferenca = valor_total - (parcela * numero_parcelas)
    valores[-1] += diferenca
    return valores


def gerar_parcelas_conta_receber(
    descricao, categoria, valor_total, vencimento_inicial, numero_parcelas,
    cliente=None, venda=None, meio_pagamento="", intervalo_dias=30,
):
    from .models import ContaReceber

    grupo = str(uuid.uuid4())[:12]
    valores = _dividir_valor(Decimal(valor_total), numero_parcelas)
    criadas = []
    for i, valor in enumerate(valores):
        criadas.append(ContaReceber.objects.create(
            descricao=descricao, categoria=categoria, valor=valor,
            vencimento=vencimento_inicial + relativedelta(days=intervalo_dias * i),
            cliente=cliente, venda=venda, meio_pagamento=meio_pagamento,
            parcela_numero=i + 1, parcela_total=numero_parcelas, grupo_parcelamento=grupo,
        ))
    return criadas


def gerar_parcelas_conta_pagar(
    descricao, categoria, valor_total, vencimento_inicial, numero_parcelas,
    fornecedor="", meio_pagamento="", intervalo_dias=30,
):
    from .models import ContaPagar

    grupo = str(uuid.uuid4())[:12]
    valores = _dividir_valor(Decimal(valor_total), numero_parcelas)
    criadas = []
    for i, valor in enumerate(valores):
        criadas.append(ContaPagar.objects.create(
            descricao=descricao, categoria=categoria, valor=valor,
            vencimento=vencimento_inicial + relativedelta(days=intervalo_dias * i),
            fornecedor=fornecedor, meio_pagamento=meio_pagamento,
            parcela_numero=i + 1, parcela_total=numero_parcelas, grupo_parcelamento=grupo,
        ))
    return criadas


def gerar_proxima_recorrencia(conta_pagar):
    """
    Cria a próxima ocorrência (1 mês depois) de uma conta a pagar
    recorrente, marcando a atual pra não gerar de novo por engano.
    """
    from .models import ContaPagar

    if not conta_pagar.recorrente or conta_pagar.proxima_gerada:
        return None

    nova = ContaPagar.objects.create(
        descricao=conta_pagar.descricao,
        fornecedor=conta_pagar.fornecedor,
        categoria=conta_pagar.categoria,
        valor=conta_pagar.valor,
        vencimento=conta_pagar.vencimento + relativedelta(months=1),
        recorrente=True,
        meio_pagamento=conta_pagar.meio_pagamento,
    )
    ContaPagar.objects.filter(pk=conta_pagar.pk).update(proxima_gerada=True)
    return nova


# --- Bancos: importação OFX e conciliação --------------------------------------

import hashlib
import re
from decimal import InvalidOperation


def parse_ofx(conteudo):
    """
    Extrai as transações de um arquivo OFX (SGML/OFX 1.0 ou XML/OFX 2.0).
    Não depende de biblioteca externa — o formato é simples o bastante
    pra um parser tolerante via regex.
    Retorna uma lista de dicts: {data, valor, descricao, fitid}.
    """
    transacoes = []
    blocos = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", conteudo, re.S | re.I)

    def _extrair(tag, bloco):
        m = re.search(rf"<{tag}>([^<\r\n]*)", bloco, re.I)
        return m.group(1).strip() if m else ""

    for bloco in blocos:
        data_raw = _extrair("DTPOSTED", bloco)
        valor_raw = _extrair("TRNAMT", bloco)
        fitid = _extrair("FITID", bloco)
        descricao = _extrair("MEMO", bloco) or _extrair("NAME", bloco)

        if not data_raw or not valor_raw:
            continue

        # DTPOSTED vem como YYYYMMDD ou YYYYMMDDHHMMSS[-3:GMT]
        data_limpa = re.match(r"(\d{4})(\d{2})(\d{2})", data_raw)
        if not data_limpa:
            continue
        from datetime import date as date_cls
        data = date_cls(int(data_limpa.group(1)), int(data_limpa.group(2)), int(data_limpa.group(3)))

        try:
            valor = Decimal(valor_raw.replace(",", "."))
        except InvalidOperation:
            continue

        if not fitid:
            # gera um identificador estável a partir do conteúdo, pra não
            # duplicar se o mesmo arquivo for importado de novo
            fitid = hashlib.md5(f"{data}-{valor}-{descricao}".encode()).hexdigest()[:20]

        transacoes.append({"data": data, "valor": valor, "descricao": descricao, "fitid": fitid})

    return transacoes


def importar_extrato_ofx(conta_bancaria, conteudo):
    from .models import ExtratoBancario

    transacoes = parse_ofx(conteudo)
    if not transacoes:
        raise ValueError("Não encontrei nenhuma transação nesse arquivo. Confira se é um OFX válido.")

    importadas = 0
    for t in transacoes:
        _, criado = ExtratoBancario.objects.get_or_create(
            conta_bancaria=conta_bancaria, fitid=t["fitid"],
            defaults={"data": t["data"], "valor": t["valor"], "descricao": t["descricao"]},
        )
        if criado:
            importadas += 1
    return importadas


def conciliar_automatico(conta_bancaria):
    """
    Tenta casar automaticamente linhas de extrato não conciliadas com
    movimentos de caixa não conciliados: mesmo valor (em módulo) e
    data em uma janela de 3 dias. Só concilia quando encontra
    exatamente 1 candidato — ambíguo demais fica pra revisão manual.
    """
    from .models import ExtratoBancario, MovimentoCaixa

    extratos = ExtratoBancario.objects.filter(conta_bancaria=conta_bancaria, conciliado=False)
    movimentos = list(MovimentoCaixa.objects.filter(conciliado=False))

    conciliados = 0
    for extrato in extratos:
        valor_abs = abs(extrato.valor)
        tipo_esperado = "entrada" if extrato.valor >= 0 else "saida"
        candidatos = [
            m for m in movimentos
            if m.tipo == tipo_esperado and m.valor == valor_abs
            and abs((m.data - extrato.data).days) <= 3
        ]
        if len(candidatos) == 1:
            candidato = candidatos[0]
            extrato.conciliado = True
            extrato.movimento_caixa = candidato
            extrato.save(update_fields=["conciliado", "movimento_caixa"])
            candidato.conciliado = True
            candidato.conta_bancaria = conta_bancaria
            candidato.save(update_fields=["conciliado", "conta_bancaria"])
            movimentos.remove(candidato)
            conciliados += 1
    return conciliados


def conciliar_manualmente(extrato, movimento_caixa):
    extrato.conciliado = True
    extrato.movimento_caixa = movimento_caixa
    extrato.save(update_fields=["conciliado", "movimento_caixa"])
    movimento_caixa.conciliado = True
    movimento_caixa.save(update_fields=["conciliado"])
