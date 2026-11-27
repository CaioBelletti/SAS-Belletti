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

    def test_vendas_fechadas_respeitam_periodo(self):
        from dateutil.relativedelta import relativedelta
        from django.utils import timezone
        from vendas.models import Venda
        agora = timezone.now()
        Venda.objects.create(status="fechada", fechada_em=agora)
        Venda.objects.create(status="fechada", fechada_em=agora - relativedelta(months=4))
        Venda.objects.create(status="aberta")
        for meses, esperado in ((3, 1), (6, 2)):
            response = self.client.get("/relatorios/", {"meses": meses})
            self.assertEqual(response.context["total_pedidos"], esperado)

    def test_receita_concilia_com_pdv(self):
        from decimal import Decimal
        from django.utils import timezone
        from catalogo.models import Produto
        from vendas.models import Venda, ItemVenda
        produto = Produto.objects.create(sku="RC9-TEST", nome="Teste")
        venda = Venda.objects.create(status="fechada", fechada_em=timezone.now(), desconto=Decimal("10"), acrescimo=Decimal("3"))
        ItemVenda.objects.create(venda=venda, produto=produto, quantidade=2, preco_unitario=Decimal("50"), desconto=Decimal("5"))
        ItemVenda.objects.create(venda=venda, produto=produto, quantidade=1, preco_unitario=Decimal("20"), desconto=Decimal("25"))
        self.assertEqual(venda.total, Decimal("88"))
        response = self.client.get("/relatorios/")
        self.assertEqual(response.context["total_valor"], venda.total)
        self.assertEqual(response.context["receita_bruta"], venda.total)
        excel = self.client.get("/relatorios/exportar/")
        wb = load_workbook(BytesIO(excel.content), read_only=True)
        resumo = dict((row[0], row[1]) for row in wb["Resumo"].values if len(row) > 1 and row[0])
        self.assertEqual(Decimal(str(resumo["Total de vendas (12 meses)"])), venda.total)
