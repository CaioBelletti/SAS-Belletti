from django.contrib.auth import get_user_model
from django.contrib.staticfiles.storage import staticfiles_storage
from django.test import TestCase
from django.urls import reverse

class WorkspaceTests(TestCase):
    def test_authenticated_dashboard_shell(self):
        user = get_user_model().objects.create_superuser(username="workspace_ci", email="workspace@example.invalid", password="test-only-password")
        self.client.force_login(user)
        response = self.client.get(reverse("relatorios:dashboard"), secure=True)
        self.assertEqual(response.status_code, 200)
        for marker in ("workspaceDock", "workspaceSearch", "workspaceTheme", "workspacePalette"):
            self.assertContains(response, marker)
        for asset in ('css/workspace.css', 'js/workspace.js'):
            self.assertContains(response, staticfiles_storage.url(asset))

    def test_dashboard_sections_cover_all_widgets(self):
        from relatorios.widgets_registry import IDS_PADRAO, SECOES_WIDGETS, montar_lista_widgets
        self.assertEqual(set(IDS_PADRAO), set(SECOES_WIDGETS))
        self.assertTrue(all(w["secoes"] for w in montar_lista_widgets(None)))

    def test_stock_movements_permission_and_workspace(self):
        from django.contrib.auth.models import Permission
        user = get_user_model().objects.create_user(username="stock_ci", password="test-only-password")
        self.client.force_login(user)
        url = reverse("catalogo:movimentacoes")
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)
        user.user_permissions.add(Permission.objects.get(content_type__app_label="catalogo", codename="view_movimentacaoestoque"))
        response = self.client.get(url, {"q": "SKU", "tipo": "entrada"}, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "workspaceDock")
        self.assertContains(response, "Nenhuma movimentação encontrada")

    def test_registration_category_create_edit_and_permissions(self):
        from catalogo.models import Categoria
        user = get_user_model().objects.create_user(username="registration_denied")
        self.client.force_login(user)
        url = reverse("registration_list", args=["categorias"])
        self.assertEqual(self.client.get(url, secure=True).status_code, 403)
        admin = get_user_model().objects.create_superuser(username="registration_admin", email="reg@example.invalid", password="test-only-password")
        self.client.force_login(admin)
        self.assertEqual(self.client.post(reverse("registration_new", args=["categorias"]), {"nome":"Categoria CI","jogo_tcg":"pokemon"}, secure=True).status_code, 302)
        obj = Categoria.objects.get(nome="Categoria CI")
        self.assertEqual(self.client.post(reverse("registration_edit", args=["categorias",obj.pk]), {"nome":"Categoria editada","jogo_tcg":"magic"}, secure=True).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.jogo_tcg,"magic")
        self.assertContains(self.client.get(url, {"q":"editada"}, secure=True), "Categoria editada")

    def test_registration_supplier_create_edit(self):
        from suprimentos.models import Fornecedor
        admin = get_user_model().objects.create_superuser(username="supplier_admin", email="supplier@example.invalid", password="test-only-password")
        self.client.force_login(admin)
        self.assertEqual(self.client.post(reverse("registration_new", args=["fornecedores"]), {"nome":"Fornecedor CI","email":"ci@example.invalid","avaliacao":"4"}, secure=True).status_code, 302)
        obj = Fornecedor.objects.get(nome="Fornecedor CI")
        self.assertEqual(self.client.post(reverse("registration_edit", args=["fornecedores",obj.pk]), {"nome":"Fornecedor editado","avaliacao":"5"}, secure=True).status_code, 302)
        obj.refresh_from_db()
        self.assertEqual(obj.avaliacao,5)
