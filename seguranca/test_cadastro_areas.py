from django.contrib.auth import get_user_model
from django.test import TestCase
from .middleware import _area_da_url


class CadastroAreaTests(TestCase):
    def test_mapeamento(self):
        for kind, area in (("clientes", "crm"), ("produtos", "catalogo"), ("categorias", "catalogo"), ("fornecedores", "suprimentos"), ("desconhecido", "admin_completo")):
            self.assertEqual(_area_da_url(f"/cadastros/{kind}/novo/"), area)

    def test_vendedor_nao_pode_contornar_area_por_cadastros(self):
        user = get_user_model().objects.create_user(username="vendedor")
        self.client.force_login(user)
        for path in ("/cadastros/produtos/", "/cadastros/fornecedores/1/excluir/", "/cadastros/clientes/novo/"):
            for method in ("get", "post"):
                response = getattr(self.client, method)(path)
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response.url, "/")
