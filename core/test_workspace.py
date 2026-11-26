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
