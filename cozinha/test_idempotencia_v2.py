import json
import uuid
from unittest.mock import patch
from django.http import JsonResponse
from django.test import TestCase, RequestFactory
from .models import RequisicaoPedido
from .views import fazer_pedido


class IdempotenciaPedidoTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.key = str(uuid.uuid4())

    def enviar(self, payload):
        request = self.factory.post("/", data=json.dumps(payload), content_type="application/json", HTTP_IDEMPOTENCY_KEY=self.key)
        return fazer_pedido(request)

    @patch("cozinha.views._fazer_pedido")
    def test_replay_and_conflict(self, criar):
        criar.return_value = JsonResponse({"ok": True, "pedido_id": 123})
        first = self.enviar({"nome": "Teste"})
        second = self.enviar({"nome": "Teste"})
        self.assertEqual(first.content, second.content)
        self.assertEqual(criar.call_count, 1)
        self.assertEqual(self.enviar({"nome": "Outro"}).status_code, 409)

    @patch("cozinha.views._fazer_pedido")
    def test_rejection_rolls_back_and_allows_retry(self, criar):
        criar.return_value = JsonResponse({"ok": False, "erro": "Indisponível"}, status=400)
        response = self.enviar({"nome": "Teste"})
        self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
        self.assertFalse(RequisicaoPedido.objects.exists())
        criar.return_value = JsonResponse({"ok": True, "pedido_id": 124})
        self.assertEqual(self.enviar({"nome": "Teste"}).status_code, 200)
