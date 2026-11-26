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

    def test_unavailable_product_creates_no_order(self):
        from .models import PedidoCozinha
        response = self.enviar({
            "nome": "Teste",
            "dispositivo_token": str(uuid.uuid4()),
            "itens": [{"prato_id": 2147483647, "quantidade": 1}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
        self.assertFalse(PedidoCozinha.objects.exists())
        self.assertFalse(RequisicaoPedido.objects.exists())

    def test_promotion_extras_are_rejected(self):
        from .models import PedidoCozinha
        response = self.enviar({
            "nome": "Teste",
            "dispositivo_token": str(uuid.uuid4()),
            "itens": [{"promocao_id": 1, "quantidade": 1, "adicionais": ["1"]}],
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("não aceita adicionais", json.loads(response.content)["erro"])
        self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
        self.assertFalse(PedidoCozinha.objects.exists())
        self.assertFalse(RequisicaoPedido.objects.exists())

    def test_malformed_payloads_are_rejected(self):
        from .models import PedidoCozinha
        payloads = [
            [], {"nome": 123, "itens": []},
            {"nome": "Teste", "itens": "incorreto"},
            {"nome": "Teste", "itens": [{"prato_id": {}, "quantidade": 1}]},
            {"nome": "Teste", "itens": [{"prato_id": 1, "observacao": []}]},
        ]
        for payload in payloads:
            with self.subTest(payload=payload):
                response = self.enviar(payload)
                self.assertEqual(response.status_code, 400)
                self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
                self.assertFalse(PedidoCozinha.objects.exists())
                self.assertFalse(RequisicaoPedido.objects.exists())

    def test_invalid_quantities_are_not_coerced(self):
        from .models import PedidoCozinha
        for quantity in (True, False, 1.5, "2", None, 0, -1, 1000):
            with self.subTest(quantity=quantity):
                response = self.enviar({"nome": "Teste", "dispositivo_token": str(uuid.uuid4()), "itens": [{"prato_id": 1, "quantidade": quantity}]})
                self.assertEqual(response.status_code, 400)
                self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
                self.assertFalse(PedidoCozinha.objects.exists())
                self.assertFalse(RequisicaoPedido.objects.exists())

    def test_malformed_tokens_are_rejected(self):
        from .models import PedidoCozinha
        for field in ("mesa_token", "participante_token"):
            for value in ("invalid", 123, [], {}):
                with self.subTest(field=field, value=value):
                    response = self.enviar({"nome": "Teste", field: value, "itens": [{"prato_id": 1, "quantidade": 1}]})
                    self.assertEqual(response.status_code, 400)
                    self.assertTrue(json.loads(response.content)["pedido_nao_criado"])
                    self.assertFalse(PedidoCozinha.objects.exists())
                    self.assertFalse(RequisicaoPedido.objects.exists())
