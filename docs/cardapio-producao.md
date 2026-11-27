# Cardápio — preparação de produção
Base aprovada: 17dd45a5a3c4ec9c295a57c0dd6957cc3a6efb0c.
Status: NÃO AUTORIZADO PARA DEPLOY.

## Pré-requisitos bloqueantes
- [ ] Confirmar projeto, ambiente, serviço, domínio e banco de produção.
- [ ] Registrar commit atualmente publicado e configuração de rollback.
- [ ] Criar backup consistente do PostgreSQL e verificar restauração em banco isolado.
- [ ] Definir DEBUG=False, SECRET_KEY exclusiva e aleatória, DATABASE_URL correta, ALLOWED_HOSTS restrito e CSRF_TRUSTED_ORIGINS HTTPS.
- [ ] Conferir proxy HTTPS, cookies, permissões de funcionários e isolamento entre mesas.
- [ ] Executar manage.py check --deploy e manage.py makemigrations --check --dry-run com configuração segura; revisar migrate --plan contra cópia do banco de produção.
- [ ] Testar migrações na cópia restaurada e executar suíte de testes.
- [ ] Validar produtos, preços, disponibilidade e dados de demonstração; não excluir registros sem autorização.
- [ ] Confirmar domínio definitivo antes de gerar QR Codes; testar cada mesa.

## Publicação controlada
O Procfile executa migrate automaticamente: não iniciar deploy antes de aprovar backup e plano de migração. Publicar commit aprovado em janela definida, verificar saúde, logs, estáticos, login, pedido, cozinha, garçom e conta. Abrir poucas mesas e monitorar erros.

## Reversão
Interromper novos pedidos se houver risco de inconsistência. Reimplantar commit anterior somente se compatível com esquema migrado. Caso contrário, executar plano de reversão de migrações previamente testado ou restaurar backup com autorização explícita, considerando pedidos posteriores ao backup. Nunca restaurar automaticamente.
