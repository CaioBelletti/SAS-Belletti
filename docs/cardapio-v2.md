# Cardápio V2 — plano de execução e critérios de aceite

## Base auditada
- cozinha/views.py: cardapio_publico, confirmar_mesa, cardapio_mesa, fazer_pedido.
- cozinha/models.py: Mesa, Comanda, ParticipanteMesa, PedidoCozinha.
- templates/cozinha/cardapio.html: carrinho local, participante, chamadas e avaliação.

## Bloqueadores de liberação
1. Substituir throttle por mesa por idempotência persistente por tentativa, com unicidade no banco e resposta reproduzível; limitar abuso separadamente.
2. Validar integralmente itens, quantidades, adicionais e preços no servidor antes de criar registros; transação atômica.
3. Garantir uma única comanda aberta por mesa sob concorrência e definir sessão de atendimento encerrável.
4. Auditar privacidade do histórico, consumo e tokens de participante; não expor pedidos alheios.
5. Testar dois celulares simultâneos, reenvio após timeout, mesa inativa, fechamento concorrente e falha parcial.
6. Confirmar backup restaurável e plano de reversão antes de migrações em produção.

## Interface
React incremental com fallback Django; build reproduzível, assets versionados e smoke test DEBUG=False. Ficha de produto acessível, opções obrigatórias, carrinho individual, confirmação e acompanhamento. Sem alteração do painel administrativo.

## Tablet
Modo quiosque gerenciado pelo sistema operacional; sessão pública sem credenciais administrativas; limpeza entre atendimentos. Plataforma ainda não definida.
