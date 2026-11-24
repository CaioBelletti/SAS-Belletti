"""Recovery codes and replay-resistant TOTP. Call only after primary authentication."""
import secrets
import re
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction
from django.utils import timezone
from .models import DoisFatores, CodigoRecuperacao

@transaction.atomic
def gerar_codigos(usuario):
    config = DoisFatores.objects.select_for_update().get(usuario=usuario, ativado=True)
    CodigoRecuperacao.objects.filter(config=config).delete()
    codes = [secrets.token_hex(16).upper() for _ in range(10)]
    CodigoRecuperacao.objects.bulk_create([
        CodigoRecuperacao(config=config, digest=make_password(code)) for code in codes
    ])
    return ["-".join(code[i:i+8] for i in range(0,32,8)) for code in codes]

@transaction.atomic
def consumir_codigo(usuario, codigo):
    normalized = str(codigo).strip().upper().replace("-", "")
    if not re.fullmatch(r"[0-9A-F]{32}", normalized):
        return False
    config = DoisFatores.objects.select_for_update().filter(usuario=usuario, ativado=True).first()
    if not config:
        return False
    for item in CodigoRecuperacao.objects.filter(config=config, usado_em__isnull=True):
        if check_password(normalized, item.digest):
            return CodigoRecuperacao.objects.filter(pk=item.pk, usado_em__isnull=True).update(usado_em=timezone.now()) == 1
    return False

@transaction.atomic
def consumir_totp(usuario, codigo):
    import pyotp
    from hmac import compare_digest
    codigo = str(codigo).strip()
    if not re.fullmatch(r"[0-9]{6}", codigo):
        return False
    config = DoisFatores.objects.select_for_update().filter(usuario=usuario, ativado=True).first()
    if not config:
        return False
    try:
        totp = pyotp.TOTP(config.secret)
        step = int(timezone.now().timestamp()) // totp.interval
        for candidate in (step+1, step, step-1):
            if candidate > config.ultimo_totp and compare_digest(totp.generate_otp(candidate), codigo):
                config.ultimo_totp = candidate
                config.save(update_fields=["ultimo_totp"])
                return True
    except (ValueError, TypeError):
        return False
    return False
