from django.db.models import F
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import HistoricoPreco, MovimentacaoEstoque, Produto


@receiver(pre_save, sender=Produto)
def _guardar_preco_anterior(sender, instance, **kwargs):
    """Guarda o preço de venda que estava no banco ANTES desse save, pra comparar depois."""
    if not instance.pk:
        instance._preco_anterior = None
        return
    anterior = Produto.objects.filter(pk=instance.pk).values_list("preco_venda", flat=True).first()
    instance._preco_anterior = anterior


@receiver(post_save, sender=Produto)
def _registrar_historico_preco(sender, instance, created, **kwargs):
    """Se o preço de venda mudou nesse save, registra no histórico."""
    anterior = getattr(instance, "_preco_anterior", None)
    if created:
        return  # não registra o preço "inicial" como uma mudança, só mudanças de verdade
    if anterior is not None and anterior != instance.preco_venda:
        HistoricoPreco.objects.create(
            produto=instance, preco_anterior=anterior, preco_novo=instance.preco_venda,
        )


@receiver(post_save, sender=MovimentacaoEstoque)
def atualizar_estoque(sender, instance, created, **kwargs):
    """Toda vez que uma movimentação é salva, ajusta o saldo do produto."""
    if not created:
        return

    if instance.tipo == "entrada":
        Produto.objects.filter(pk=instance.produto_id).update(
            estoque_atual=F("estoque_atual") + instance.quantidade
        )
    elif instance.tipo == "saida":
        Produto.objects.filter(pk=instance.produto_id).update(
            estoque_atual=F("estoque_atual") - instance.quantidade
        )
    # "ajuste" é tratado à parte, chamando o update manualmente na view/admin
    # que cria a movimentação, para permitir tanto soma quanto subtração.

    _verificar_alerta_estoque(instance.produto_id)


def _verificar_alerta_estoque(produto_id):
    """
    Manda um alerta (uma vez só) quando o produto cruza pra baixo do
    estoque mínimo. Se for reabastecido depois, o alerta reseta —
    assim um novo alerta dispara se cair de novo no futuro.
    """
    from notificacoes.services import notificar

    produto = Produto.objects.get(pk=produto_id)
    if produto.estoque_baixo and not produto.alerta_estoque_enviado:
        Produto.objects.filter(pk=produto_id).update(alerta_estoque_enviado=True)
        notificar(
            "Estoque baixo",
            f"O produto {produto.nome} ({produto.sku}) está com estoque baixo: "
            f"{produto.estoque_atual} unidade(s) (mínimo configurado: {produto.estoque_minimo}).",
        )
    elif not produto.estoque_baixo and produto.alerta_estoque_enviado:
        Produto.objects.filter(pk=produto_id).update(alerta_estoque_enviado=False)
