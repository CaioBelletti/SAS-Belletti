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
        response = self.client.get(url, secure=True)
        self.assertRedirects(response, "/", fetch_redirect_response=False)
        user.is_staff = True
        user.save(update_fields=["is_staff"])
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

    def test_supplier_delete_confirmation_and_protection(self):
        from suprimentos.models import Fornecedor, OrdemCompra
        admin = get_user_model().objects.create_superuser(username="delete_admin",email="delete@example.invalid",password="test-only-password")
        self.client.force_login(admin)
        obj = Fornecedor.objects.create(nome="Descartavel")
        url = reverse("supplier_delete",args=[obj.pk])
        self.assertEqual(self.client.get(url,secure=True).status_code,200)
        self.assertTrue(Fornecedor.objects.filter(pk=obj.pk).exists())
        self.assertEqual(self.client.post(url,secure=True).status_code,302)
        self.assertFalse(Fornecedor.objects.filter(pk=obj.pk).exists())
        linked = Fornecedor.objects.create(nome="Historico")
        OrdemCompra.objects.create(fornecedor=linked)
        self.client.post(reverse("supplier_delete",args=[linked.pk]),secure=True)
        self.assertTrue(Fornecedor.objects.filter(pk=linked.pk).exists())

    def test_native_registration_and_catalog_pages(self):
        admin = get_user_model().objects.create_superuser(username="catalog_admin",email="catalog@example.invalid",password="test-only-password")
        self.client.force_login(admin)
        for kind in ("clientes","produtos","fornecedores","categorias"):
            for name in ("registration_list","registration_new"):
                response = self.client.get(reverse(name,args=[kind]),secure=True)
                self.assertEqual(response.status_code,200,(kind,name))
        for name in ("etiquetas","consulta_carta","composicao","inventario","perdas","reservas"):
            response = self.client.get(reverse("catalogo:"+name),secure=True)
            self.assertEqual(response.status_code,200,name)

    def test_client_registration(self):
        from vendas.models import Cliente
        admin = get_user_model().objects.create_superuser(username="client_admin",email="client@example.invalid",password="test-only-password")
        self.client.force_login(admin)
        response = self.client.post(reverse("registration_new",args=["clientes"]),{"nome":"Cliente CI"},secure=True)
        self.assertEqual(response.status_code,302)
        self.assertTrue(Cliente.objects.filter(nome="Cliente CI").exists())

    def test_sales_history_permission(self):
        user = get_user_model().objects.create_user(username="sales_history",is_staff=True)
        self.client.force_login(user)
        url = reverse("vendas:historico")
        self.assertEqual(self.client.get(url,secure=True).status_code,403)
        from django.contrib.auth.models import Permission
        user.user_permissions.add(Permission.objects.get(content_type__app_label="vendas",codename="view_venda"))
        self.assertEqual(self.client.get(url,secure=True).status_code,200)
