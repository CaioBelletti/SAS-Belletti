from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import ContaPagar


@receiver(pre_save, sender=ContaPagar)
def bloquear_pagamento_sem_aprovacao(sender, instance, **kwargs):
    """
    Se essa conta está sendo marcada como paga agora (não já estava)
    e o valor exige aprovação, reverte a mudança — a conta só vira
    'pago' de verdade depois que a aprovação for concedida (ver
    aprovacoes.services.decidir, que atualiza o pagamento na hora
    de finalizar a aprovação).
    """
    if getattr(instance, "_pulando_verificacao_aprovacao", False):
        return
    if not instance.pk:
        return
    status_anterior = ContaPagar.objects.filter(pk=instance.pk).values_list("status", flat=True).first()
    if status_anterior == "pago" or instance.status != "pago":
        return

    from aprovacoes.services import verificar_aprovacao_pagamento
    if verificar_aprovacao_pagamento(instance):
        instance.status = status_anterior


@receiver(post_save, sender=ContaPagar)
def gerar_recorrencia_ao_pagar(sender, instance, created, **kwargs):
    if created:
        return
    if instance.status == "pago" and instance.recorrente and not instance.proxima_gerada:
        from .services import gerar_proxima_recorrencia
        gerar_proxima_recorrencia(instance)
