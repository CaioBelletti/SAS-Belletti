from datetime import timedelta
from unittest.mock import patch
import pyotp
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from .models import DoisFatores, CodigoRecuperacao
from .recovery import gerar_codigos, consumir_codigo, consumir_totp
from .services import registrar_tentativa, segundos_restantes_bloqueio, verificar_codigo_totp

@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthV2Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="auth-test", password="test-password")
        self.config = DoisFatores.objects.create(usuario=self.user, secret=pyotp.random_base32(), ativado=True)

    def test_recovery_single_use(self):
        codes = gerar_codigos(self.user)
        self.assertEqual(len(set(codes)), 10)
        self.assertEqual(CodigoRecuperacao.objects.filter(config=self.config).count(), 10)
        self.assertTrue(consumir_codigo(self.user, codes[0]))
        self.assertFalse(consumir_codigo(self.user, codes[0]))

    def test_regeneration(self):
        old = gerar_codigos(self.user)
        new = gerar_codigos(self.user)
        self.assertFalse(consumir_codigo(self.user, old[0]))
        self.assertTrue(consumir_codigo(self.user, new[0]))

    def test_totp_replay(self):
        now = timezone.now()
        with patch("seguranca.recovery.timezone.now", return_value=now):
            code = pyotp.TOTP(self.config.secret).at(now)
            self.assertTrue(consumir_totp(self.user, code))
            self.assertFalse(consumir_totp(self.user, code))

    def test_malformed(self):
        self.assertFalse(verificar_codigo_totp(self.config.secret, "abc"))
        self.assertFalse(consumir_codigo(self.user, "abc"))

    def test_lockout(self):
        now = timezone.now()
        for _ in range(4):
            registrar_tentativa("auth-test", False)
        self.assertEqual(segundos_restantes_bloqueio("auth-test"), 0)
        registrar_tentativa("auth-test", False)
        self.assertGreater(segundos_restantes_bloqueio("AUTH-TEST"), 0)
        with patch("seguranca.services.timezone.now", return_value=now+timedelta(minutes=16)):
            self.assertEqual(segundos_restantes_bloqueio("auth-test"), 0)
