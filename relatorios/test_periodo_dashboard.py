from io import BytesIO
from django.contrib.auth import get_user_model
from django.test import TestCase
from openpyxl import load_workbook


class PeriodoDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(username="periodo_test", is_staff=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_periodos_e_fallback(self):
        for valor, esperado in (("1", 1), ("3", 3), ("6", 6), ("12", 12), ("999", 12), ("abc", 12)):
            with self.subTest(valor=valor):
                response = self.client.get("/relatorios/", {"meses": valor})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.context["periodo_meses"], esperado)
                self.assertContains(response, f"?meses={esperado}")

    def test_excel_periodo(self):
        response = self.client.get("/relatorios/exportar/", {"meses": "3"})
        self.assertEqual(response.status_code, 200)
        wb = load_workbook(BytesIO(response.content), read_only=True)
        self.assertIn("Total de vendas (3 meses)", [row[0] for row in wb["Resumo"].values if row])
