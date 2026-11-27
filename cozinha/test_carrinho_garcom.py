import json
import uuid
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from .models import ChamadoAtendente, Mesa, PedidoCozinha, Prato


class CarrinhoIsoladoTests(TestCase):
    def pedir(self, client, mesa, prato, nome, qtd):
        payload = {"nome": nome, "mesa_token": str(mesa.token_publico), "dispositivo_token": str(uuid.uuid4()),
                   "itens": [{"prato_id": prato.pk, "quantidade": qtd}]}
        return client.post(reverse("fazer_pedido"), data=json.dumps(payload), content_type="application/json",
                           HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4()), secure=True)

    def test_carrinhos_de_clientes_nao_se_misturam(self):
        mesa = Mesa.objects.create(numero=9101)
        prato = Prato.objects.create(nome="CI-RC10 prato", preco=Decimal("10.00"))
        a, b = self.pedir(Client(), mesa, prato, "CI-A", 1), self.pedir(Client(), mesa, prato, "CI-B", 3)
        self.assertEqual((a.status_code, b.status_code), (200, 200))
        qtds = {p.nome_para_chamar: sum(i.quantidade for i in p.itens.all()) for p in PedidoCozinha.objects.all()}
        self.assertEqual(qtds, {"CI-A": 1, "CI-B": 3})

    def test_item_invalido_nao_cria_pedido(self):
        mesa = Mesa.objects.create(numero=9102)
        prato = Prato.objects.create(nome="CI-RC10 x", preco=Decimal("10.00"))
        r = self.pedir(Client(), mesa, prato, "CI-C", 0)
        self.assertEqual(r.status_code, 400)
        self.assertFalse(PedidoCozinha.objects.exists())


class GarcomPermissaoTests(TestCase):
    def test_anonimo_nao_acessa_painel(self):
        for name in ("painel_garcom", "dados_garcom"):
            r = self.client.get(reverse(f"cozinha:{name}"), secure=True)
            self.assertEqual(r.status_code, 302, name)
            self.assertIn("login", r["Location"])

    def test_chamado_aparece_e_e_atendido_uma_vez(self):
        mesa = Mesa.objects.create(numero=9103)
        chamado = ChamadoAtendente.objects.create(mesa=mesa, tipo="atendente")
        staff = Client()
        staff.force_login(get_user_model().objects.create_user("ci_garcom", password="test-only", is_staff=True))
        ids = [c["id"] for c in staff.get(reverse("cozinha:dados_garcom"), secure=True).json()["chamados"]]
        self.assertEqual(ids, [chamado.pk])
        self.assertEqual(staff.post(reverse("cozinha:atender_chamado", args=[chamado.pk]), secure=True).status_code, 200)
        self.assertEqual(staff.get(reverse("cozinha:dados_garcom"), secure=True).json()["chamados"], [])
