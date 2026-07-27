from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver


@receiver(user_logged_out)
def remover_sessao_ativa(sender, request, user, **kwargs):
    from .models import SessaoAtiva
    if request and request.session.session_key:
        SessaoAtiva.objects.filter(session_key=request.session.session_key).delete()
