# Homologação Belletti Auth 2.0

Não alterar o serviço de produção. Criar serviço/projeto separado no Railway, conectado à branch feature/auth-v2, com PostgreSQL próprio e dados fictícios. Não copiar DATABASE_URL, SECRET_KEY ou volumes de produção.

Selecionar Nixpacks caso disponível, conferir que o build executa npm run build e gera static/auth-v2/auth.js e auth.css antes do Procfile. Caso o builder seja outro, configurar explicitamente a etapa equivalente, preservando Python e Tesseract.

Variáveis: DATABASE_URL referenciando exclusivamente o PostgreSQL de homologação, SECRET_KEY nova e aleatória, DEBUG=False. Gerar domínio próprio e conferir ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS. Criar usuário fictício via python manage.py createsuperuser no shell de homologação.

Validar login, senha incorreta, TOTP, recuperação única, bloqueio, expiração, configuração 2FA, fallback sem JavaScript, CSRF, rotas alternativas de login, visual desktop/mobile e regressão dos módulos existentes. Conferir logs e ausência de segredos.

Não fazer merge ou deploy de produção sem aprovação explícita, backup verificável e plano de rollback. Não reverter migração destrutivamente: códigos de recuperação seriam perdidos.


## Ensaio de reversão (somente homologação)

1. Registrar SHA do deploy ativo, SHA anterior, versão PostgreSQL e migrações aplicadas.
2. Criar backup consistente do PostgreSQL de homologação e dos arquivos persistentes. Guardar credenciais e backups fora do Git.
3. Restaurar o backup em outro banco isolado; verificar integridade, contagens e acesso com conta fictícia.
4. Testar o deploy anterior contra uma cópia do banco já migrado. Não reverter migrações automaticamente.
5. Se incompatível, ensaiar restauração do backup e deploy anterior juntos, registrando duração e eventual perda de dados.
6. Validar login, 2FA, recuperação, permissões e operações essenciais após restauração.
7. Registrar evidências, responsáveis, horário e resultado. Não executar este procedimento na produção sem autorização explícita.

## CRM

O PR Auth V2 não altera arquivos crm/. Diagnosticar com
`python manage.py makemigrations crm --dry-run --verbosity 3` em ambiente isolado.
Revisar a diferença antes de criar qualquer migração em PR separado.
