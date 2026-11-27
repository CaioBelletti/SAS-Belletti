from datetime import date
from decimal import Decimal
from io import BytesIO
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook
from .models import ContaBancaria, ExtratoBancario, MovimentoCaixa
from .services import conciliar_automatico

OFX = """<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKTRANLIST>
<STMTTRN><TRNTYPE>CREDIT<DTPOSTED>20261127<TRNAMT>50.00<FITID>CI-RC10-001<MEMO>SINTETICO CI
</STMTTRN></BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"""


class ConciliacaoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser("ci_conc", "ci@example.invalid", "test-only-password")
        self.client.force_login(self.user)
        self.conta = ContaBancaria.objects.create(nome="CI-RC10 conta sintética")

    def test_auto_concilia_unico_candidato_e_ignora_ambiguo(self):
        unico = MovimentoCaixa.objects.create(tipo="entrada", valor=Decimal("50"), descricao="CI-RC10 a", data=date(2026, 11, 27))
        ExtratoBancario.objects.create(conta_bancaria=self.conta, data=date(2026, 11, 28), valor=Decimal("50"), fitid="CI-A")
        self.assertEqual(conciliar_automatico(self.conta), 1)
        unico.refresh_from_db()
        self.assertTrue(unico.conciliado)
        for n in ("b", "c"):
            MovimentoCaixa.objects.create(tipo="saida", valor=Decimal("9"), descricao=f"CI-RC10 {n}", data=date(2026, 11, 27))
        ExtratoBancario.objects.create(conta_bancaria=self.conta, data=date(2026, 11, 27), valor=Decimal("-9"), fitid="CI-B")
        self.assertEqual(conciliar_automatico(self.conta), 0)

    def test_importar_ofx_idempotente_e_conciliar_via_http(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        url = reverse("financeiro:importar_ofx", args=[self.conta.pk])
        for _ in range(2):
            self.client.post(url, {"arquivo": SimpleUploadedFile("x.ofx", OFX.encode())}, secure=True)
        self.assertEqual(self.conta.extratos.filter(fitid="CI-RC10-001").count(), 1)
        MovimentoCaixa.objects.create(tipo="entrada", valor=Decimal("50"), descricao="CI-RC10 m", data=date(2026, 11, 27))
        r = self.client.post(reverse("financeiro:conciliar", args=[self.conta.pk]), {"acao": "auto"}, secure=True)
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.conta.extratos.get(fitid="CI-RC10-001").conciliado)

    def test_anonimo_nao_concilia(self):
        self.client.logout()
        r = self.client.post(reverse("financeiro:conciliar", args=[self.conta.pk]), {"acao": "auto"}, secure=True)
        self.assertEqual(r.status_code, 302)
        self.assertIn("login", r["Location"])

    def test_dashboard_e_excel(self):
        self.assertEqual(self.client.get("/relatorios/", secure=True).status_code, 200)
        r = self.client.get("/relatorios/exportar/", {"meses": "3"}, secure=True)
        self.assertEqual(r.status_code, 200)
        self.assertIn("Resumo", load_workbook(BytesIO(r.content), read_only=True).sheetnames)
