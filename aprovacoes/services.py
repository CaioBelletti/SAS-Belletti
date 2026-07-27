from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils import timezone

from .models import NivelAprovacao, RegistroDecisao, RegraAprovacao, SolicitacaoAprovacao


class AprovacaoJaDecididaError(Exception):
    pass


class SemPermissaoParaAprovarError(Exception):
    pass


def precisa_aprovacao(tipo, valor):
    """Verifica se essa operação, com esse valor, precisa passar por aprovação."""
    regra = RegraAprovacao.objects.filter(tipo=tipo, ativa=True).first()
    if not regra:
        return False
    return valor > regra.valor_limite


@transaction.atomic
def solicitar_aprovacao(tipo, objeto, valor, descricao, solicitante):
    """Cria a solicitação de aprovação, já no nível 1."""
    return SolicitacaoAprovacao.objects.create(
        content_type=ContentType.objects.get_for_model(objeto),
        object_id=objeto.pk,
        tipo=tipo,
        descricao=descricao,
        valor=valor,
        solicitado_por=solicitante,
        nivel_atual=1,
        status="pendente",
    )


def usuario_pode_aprovar(usuario, solicitacao):
    if usuario.is_superuser:
        return True
    grupo_necessario = solicitacao.grupo_do_nivel_atual()
    if not grupo_necessario:
        return False
    return usuario.groups.filter(pk=grupo_necessario.pk).exists()


@transaction.atomic
def decidir(solicitacao, usuario, decisao, comentario=""):
    """
    Processa uma decisão (aprovar/rejeitar) no nível atual.
    - Rejeitar em qualquer nível encerra tudo como rejeitada.
    - Aprovar avança pro próximo nível, ou finaliza como aprovada se
      esse já era o último nível.
    Devolve a solicitação atualizada.
    """
    if solicitacao.status != "pendente":
        raise AprovacaoJaDecididaError("Essa solicitação já foi decidida.")

    if not usuario_pode_aprovar(usuario, solicitacao):
        raise SemPermissaoParaAprovarError("Seu perfil não pode aprovar esse nível.")

    RegistroDecisao.objects.create(
        solicitacao=solicitacao, nivel=solicitacao.nivel_atual,
        aprovador=usuario, decisao=decisao, comentario=comentario,
    )

    if decisao == "rejeitado":
        solicitacao.status = "rejeitada"
        solicitacao.finalizada_em = timezone.now()
        solicitacao.save(update_fields=["status", "finalizada_em"])
        return solicitacao

    total_niveis = solicitacao.total_niveis
    if solicitacao.nivel_atual >= total_niveis:
        solicitacao.status = "aprovada"
        solicitacao.finalizada_em = timezone.now()
        solicitacao.save(update_fields=["status", "finalizada_em"])
        _liberar_apos_aprovacao(solicitacao)
    else:
        solicitacao.nivel_atual += 1
        solicitacao.save(update_fields=["nivel_atual"])

    return solicitacao


def _liberar_apos_aprovacao(solicitacao):
    """Executa a ação de verdade que estava esperando aprovação completa."""
    objeto = solicitacao.objeto
    if objeto is None:
        return

    if solicitacao.tipo == "compra":
        objeto.status = "aberta"
        objeto.save(update_fields=["status"])

    elif solicitacao.tipo == "pagamento":
        from django.utils import timezone as tz
        objeto._pulando_verificacao_aprovacao = True
        objeto.status = "pago"
        objeto.data_pagamento = tz.localdate()
        objeto.save(update_fields=["status", "data_pagamento"])

    elif solicitacao.tipo == "desconto":
        from vendas.services import fechar_venda
        objeto.status = "aberta"
        objeto.save(update_fields=["status"])
        fechar_venda(objeto)


def verificar_aprovacao_compra(ordem):
    """
    Chamar depois que os itens da ordem já foram todos criados.
    Se o valor total exigir aprovação, coloca a ordem em
    'pendente_aprovacao' e cria a solicitação — senão, deixa 'aberta'
    normalmente (comportamento de sempre).
    """
    if precisa_aprovacao("compra", ordem.valor_total):
        ordem.status = "pendente_aprovacao"
        ordem.save(update_fields=["status"])
        solicitar_aprovacao(
            "compra", ordem, ordem.valor_total,
            f"Ordem de compra #{ordem.pk} — {ordem.fornecedor.nome}",
            solicitante=None,
        )
        return True
    return False


def verificar_aprovacao_pagamento(conta_pagar, solicitante=None):
    """
    Chamar antes de marcar uma conta a pagar como paga. Se precisar
    de aprovação e ainda não tiver uma solicitação pendente pra essa
    conta, cria e devolve True (bloqueando o pagamento direto).
    """
    if not precisa_aprovacao("pagamento", conta_pagar.valor):
        return False

    from django.contrib.contenttypes.models import ContentType
    ja_tem_pendente = SolicitacaoAprovacao.objects.filter(
        content_type=ContentType.objects.get_for_model(conta_pagar),
        object_id=conta_pagar.pk, status="pendente",
    ).exists()
    if ja_tem_pendente:
        return True

    solicitar_aprovacao(
        "pagamento", conta_pagar, conta_pagar.valor,
        f"Pagamento — {conta_pagar.descricao}", solicitante=solicitante,
    )
    return True
