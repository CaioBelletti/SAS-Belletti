# RC10 — homologação

Serviço: `cardapio-homologacao` (ambiente `homologacao`), domínio cardapio-homologacao-homologacao.up.railway.app.
Estado antes: branch `release/belletti-rc9`, SHA `af493a58073cf61010991ab94592c5e13706db5c` (deploy d9edbcb4, SUCCESS).

## Segurança de migrações
Nenhum arquivo de migração difere entre rc9 e rc10 (`git diff --name-only`); `migrate --plan` sem operações;
`makemigrations --check` sem mudanças. Nenhuma operação de schema no deploy.

## Backup / rollback
- Nenhum backup do Postgres de homologação foi verificado; antes de mudanças de schema, criar backup no painel Railway.
- Rollback de código: redeploy do deployment d9edbcb4 (rc9, af493a5) ou apontar o serviço de volta a `release/belletti-rc9`.
  Como não há migração, o rollback não exige reverter banco.
- Dados sintéticos de validação usam o prefixo `CI-RC10` / `VAL-RC10` e são removíveis por ID exato.

## Testes
`python manage.py test` — 56 testes OK em SQLite e em PostgreSQL 18 isolado (container descartável).
Novos: `cozinha/test_carrinho_garcom.py`, `financeiro/test_conciliacao.py`. CI: `.github/workflows/integracao-ci.yml` (branches `integration/**`).

## CI
O push do workflow foi recusado (a GitHub App não tem a permissão `workflows`). O arquivo pronto está em `docs/ci/integracao-ci.yml`:
copiar para `.github/workflows/integracao-ci.yml` com um token que tenha essa permissão.

## Deploy RC10
- Deployment 96a474b6 (SUCCESS), branch `integration/cardapio-workspace-rc10`, SHA `e4e9c2fb6e371c00025ea339d3ed0351ff2d14ee`.
- Pre-deploy: "No migrations to apply"; seed idempotente; 17 testes de cozinha OK (banco de teste separado, destruído ao fim). Gunicorn iniciou na 8080.
- HTTP anônimo: `/login/` 200; `/relatorios/`, `/relatorios/exportar/`, `/financeiro/bancos/`, `/admin/` e `/cozinha/garcom/` redirecionam ao login; estáticos 200.
- Não executado: login autenticado e ponta a ponta com dados sintéticos (sem credenciais de teste na sessão; criar dados exigiria escrever no banco de homologação sem rotina de limpeza por ID).
