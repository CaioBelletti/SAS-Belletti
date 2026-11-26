from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from financeiro.models import CaixaSessao

class CaixaWorkspaceTest(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("operador_ci", "ci@example.invalid", "test-only-password")
        self.client.force_login(self.user)
        self.url = reverse("financeiro:caixa")

    def post(self, **data):
        response = self.client.post(self.url, data, secure=True)
        self.assertEqual(response.status_code, 302)

    def test_ciclo_caixa(self):
        self.assertEqual(self.client.get(self.url, secure=True).status_code, 200)
        self.post(acao="abrir", valor_abertura="100,00")
        sessao = CaixaSessao.objects.get(aberta_por=self.user)
        self.post(acao="suprimento", valor="20,00")
        self.post(acao="sangria", valor="10,00")
        sessao.refresh_from_db()
        self.assertEqual(sessao.saldo_esperado, Decimal("110.00"))
        self.post(acao="fechar", valor_fechamento="110,00")
        sessao.refresh_from_db()
        self.assertIsNotNone(sessao.fechada_em)
        self.assertEqual(sessao.diferenca, Decimal("0.00"))
