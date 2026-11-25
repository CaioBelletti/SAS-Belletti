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

    
class ProductionSettingsTests(TestCase):
    def run_settings(self, **overrides):
        import os, subprocess, sys
        env = os.environ.copy()
        env.update(DEBUG="False", SECRET_KEY="abc123XYZ!" * 6,
                   DATABASE_URL="postgresql://user:pass@localhost/test")
        env.update(overrides)
        return subprocess.run(
            [sys.executable, "-c", "import core.settings"],
            env=env, capture_output=True, text=True, timeout=20,
        )

    def test_valid_production_settings(self):
        self.assertEqual(self.run_settings().returncode, 0)

    def test_invalid_production_settings(self):
        for overrides, message in [
            ({"SECRET_KEY": ""}, "SECRET_KEY"),
            ({"SECRET_KEY": "short"}, "SECRET_KEY"),
            ({"DATABASE_URL": ""}, "DATABASE_URL"),
            ({"DATABASE_URL": "sqlite:///:memory:"}, "PostgreSQL"),
        ]:
            with self.subTest(overrides=overrides):
                result = self.run_settings(**overrides)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])
class AuthHTTPTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="http-auth", password="test-password", is_staff=True, is_superuser=True
        )
        self.config = DoisFatores.objects.create(
            usuario=self.user, secret=pyotp.random_base32(), ativado=True
        )

    def test_login_2fa_logout(self):
        from django.urls import reverse
        response = self.client.post(reverse("login"), {"username": self.user.username, "password": "test-password"})
        self.assertRedirects(response, reverse("seguranca:verificar_2fa"), fetch_redirect_response=False)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("relatorios:dashboard")).status_code, 302)
        response = self.client.post(reverse("seguranca:verificar_2fa"), {"codigo": pyotp.TOTP(self.config.secret).now()})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.user.pk)
        self.client.post(reverse("logout"))
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(self.client.get(reverse("relatorios:dashboard")).status_code, 302)

    def test_csrf_required(self):
        from django.test import Client
        from django.urls import reverse
        client = Client(enforce_csrf_checks=True)
        self.assertEqual(client.post(reverse("login"), {"username": self.user.username, "password": "test-password"}).status_code, 403)

    def test_admin_login_cannot_bypass_2fa(self):
        response = self.client.post("/admin/login/", {"username": self.user.username, "password": "test-password"})
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertEqual(response.status_code, 302)
