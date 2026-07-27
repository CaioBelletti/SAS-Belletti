import secrets

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = (
        "Cria um usuário PostgreSQL SOMENTE LEITURA, pra conectar o Power BI "
        "(ou qualquer outra ferramenta de BI) direto no banco sem dar acesso de "
        "escrita. Só funciona em PostgreSQL (produção/Railway) — em SQLite "
        "(local) não existe esse conceito de usuário de banco."
    )

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="powerbi_leitura")

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write(self.style.ERROR(
                "Esse comando só funciona com PostgreSQL. Localmente (SQLite) não "
                "tem usuário de banco — pra testar isso, use no ambiente do Railway."
            ))
            return

        usuario = options["usuario"]
        senha = secrets.token_urlsafe(24)

        with connection.cursor() as cursor:
            cursor.execute(f"DROP ROLE IF EXISTS {usuario};")
            cursor.execute(f"CREATE ROLE {usuario} WITH LOGIN PASSWORD %s;", [senha])
            cursor.execute(f"GRANT CONNECT ON DATABASE {connection.settings_dict['NAME']} TO {usuario};")
            cursor.execute(f"GRANT USAGE ON SCHEMA public TO {usuario};")
            cursor.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {usuario};")
            cursor.execute(
                f"ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO {usuario};"
            )

        self.stdout.write(self.style.SUCCESS(f"Usuário '{usuario}' criado com sucesso."))
        self.stdout.write("")
        self.stdout.write("Guarde essa senha AGORA — ela não é salva em lugar nenhum, só aparece essa vez:")
        self.stdout.write(self.style.WARNING(senha))
        self.stdout.write("")
        self.stdout.write("Use esses dados no Power BI Desktop (Obter dados → Banco de dados PostgreSQL):")
        self.stdout.write(f"  Servidor: {connection.settings_dict['HOST']}:{connection.settings_dict['PORT']}")
        self.stdout.write(f"  Banco de dados: {connection.settings_dict['NAME']}")
        self.stdout.write(f"  Usuário: {usuario}")
        self.stdout.write("  Senha: (a de cima)")
        self.stdout.write("")
        self.stdout.write("Tabelas recomendadas pra usar no Power BI: vw_bi_vendas, vw_bi_itens_venda, "
                           "vw_bi_estoque, vw_bi_financeiro (já vêm com os dados juntos e prontos).")
