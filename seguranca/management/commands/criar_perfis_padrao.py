from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand

from seguranca.models import Area, PerfilAcesso

AREAS_PADRAO = [
    ("pdv", "PDV"),
    ("financeiro", "Financeiro (inclui Caixa)"),
    ("catalogo", "Catálogo / Estoque"),
    ("suprimentos", "Suprimentos / Compras"),
    ("relatorios", "Relatórios / Dashboard"),
    ("crm", "CRM"),
    ("cozinha", "Cozinha / Cardápio"),
    ("admin_completo", "Painel administrativo completo"),
]

PERFIS_PADRAO = {
    "Gerente": {"acesso_total": True, "areas": []},
    "Vendedor": {"acesso_total": False, "areas": ["pdv", "financeiro"]},
    "Financeiro": {"acesso_total": False, "areas": ["financeiro", "relatorios"]},
    "Estoquista": {"acesso_total": False, "areas": ["catalogo", "suprimentos"]},
}


class Command(BaseCommand):
    help = "Cria as áreas do sistema e os perfis de acesso padrão (Gerente, Vendedor, Financeiro, Estoquista)."

    def handle(self, *args, **options):
        areas_criadas = {}
        for codigo, nome in AREAS_PADRAO:
            area, criado = Area.objects.get_or_create(codigo=codigo, defaults={"nome": nome})
            areas_criadas[codigo] = area
            if criado:
                self.stdout.write(f"  + área criada: {nome}")

        for nome_grupo, config in PERFIS_PADRAO.items():
            grupo, criado = Group.objects.get_or_create(name=nome_grupo)
            if criado:
                self.stdout.write(f"+ grupo criado: {nome_grupo}")
            perfil, _ = PerfilAcesso.objects.get_or_create(
                grupo=grupo, defaults={"acesso_total": config["acesso_total"]}
            )
            if config["areas"]:
                perfil.areas.set([areas_criadas[c] for c in config["areas"]])

        self.stdout.write(self.style.SUCCESS("Áreas e perfis padrão prontos."))
