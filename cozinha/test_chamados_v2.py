from django.test import TestCase
from django.urls import reverse
from .models import Mesa, ChamadoAtendente


class ChamadosV2Tests(TestCase):
    def setUp(self):
        self.mesa = Mesa.objects.create(numero=987)
        self.url = reverse("chamar_atendente", args=[self.mesa.token_publico])

    def test_repeated_call_reuses_pending_record(self):
        first = self.client.post(self.url, {"tipo": "atendente"})
        second = self.client.post(self.url, {"tipo": "atendente"})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["chamado_id"], second.json()["chamado_id"])
        self.assertEqual(ChamadoAtendente.objects.count(), 1)

    def test_completed_call_can_be_requested_again(self):
        first = self.client.post(self.url, {"tipo": "atendente"}).json()
        ChamadoAtendente.objects.filter(pk=first["chamado_id"]).update(atendido=True)
        second = self.client.post(self.url, {"tipo": "atendente"}).json()
        self.assertNotEqual(first["chamado_id"], second["chamado_id"])

    def test_inactive_table_and_invalid_type(self):
        self.assertEqual(self.client.post(self.url, {"tipo": "invalid"}).status_code, 400)
        self.mesa.ativa = False
        self.mesa.save(update_fields=["ativa"])
        self.assertEqual(self.client.post(self.url, {"tipo": "atendente"}).status_code, 409)
        self.assertFalse(ChamadoAtendente.objects.exists())
