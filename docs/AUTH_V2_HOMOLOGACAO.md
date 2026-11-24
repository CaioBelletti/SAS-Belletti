# Homologação Belletti Auth 2.0

Não alterar o serviço de produção. Criar serviço/projeto separado no Railway, conectado à branch feature/auth-v2, com PostgreSQL próprio e dados fictícios. Não copiar DATABASE_URL, SECRET_KEY ou volumes de produção.

Selecionar Nixpacks caso disponível, conferir que o build executa npm run build e gera static/auth-v2/auth.js e auth.css antes do Procfile. Caso o builder seja outro, configurar explicitamente a etapa equivalente, preservando Python e Tesseract.

Variáveis: DATABASE_URL referenciando exclusivamente o PostgreSQL de homologação, SECRET_KEY nova e aleatória, DEBUG=False. Gerar domínio próprio e conferir ALLOWED_HOSTS e CSRF_TRUSTED_ORIGINS. Criar usuário fictício via python manage.py createsuperuser no shell de homologação.

Validar login, senha incorreta, TOTP, recuperação única, bloqueio, expiração, configuração 2FA, fallback sem JavaScript, CSRF, rotas alternativas de login, visual desktop/mobile e regressão dos módulos existentes. Conferir logs e ausência de segredos.

Não fazer merge ou deploy de produção sem aprovação explícita, backup verificável e plano de rollback. Não reverter migração destrutivamente: códigos de recuperação seriam perdidos.
