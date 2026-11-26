from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

class WorkspaceTests(TestCase):
    def test_authenticated_dashboard_shell(self):
        user = get_user_model().objects.create_superuser(username="workspace_ci", email="workspace@example.invalid", password="test-only-password")
        self.client.force_login(user)
        response = self.client.get(reverse("relatorios:dashboard"), secure=True)
        self.assertEqual(response.status_code, 200)
        for marker in ("workspaceDock", "workspaceSearch", "workspaceTheme", "workspacePalette", "workspace.css", "workspace.js"):
            self.assertContains(response, marker)
