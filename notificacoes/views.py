import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from .models import InscricaoPush, get_config_push


@login_required
@require_GET
def api_chave_publica_push(request):
    config = get_config_push()
    return JsonResponse({"chave_publica": config.chave_publica})


@login_required
@require_POST
def api_inscrever_push(request):
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "erro": "Dados inválidos."}, status=400)

    endpoint = dados.get("endpoint")
    keys = dados.get("keys", {})
    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not (endpoint and p256dh and auth):
        return JsonResponse({"ok": False, "erro": "Inscrição incompleta."}, status=400)

    InscricaoPush.objects.update_or_create(
        endpoint=endpoint,
        defaults={"usuario": request.user, "p256dh_key": p256dh, "auth_key": auth},
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_desinscrever_push(request):
    try:
        dados = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"ok": False}, status=400)

    endpoint = dados.get("endpoint")
    if endpoint:
        InscricaoPush.objects.filter(endpoint=endpoint).delete()
    return JsonResponse({"ok": True})
