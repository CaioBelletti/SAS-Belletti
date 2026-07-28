# Painel do Garçom com alertas sonoros

Arquivos alterados:
- cozinha/views.py
- cozinha/urls.py
- templates/base.html
- templates/cozinha/painel_garcom.html

Não há migration nesta atualização.

## Uso
1. Abra `/cozinha/garcom/` com um usuário autenticado.
2. Clique em **Ativar alertas sonoros** uma vez ao abrir a página.
3. Mantenha a página aberta no celular, tablet ou computador do garçom.

O painel consulta o servidor a cada 5 segundos e toca sons diferentes para:
- nova chamada de mesa;
- novo pedido no status `pronto`.

Ações disponíveis:
- assumir chamada;
- levar pedido à mesa;
- confirmar entrega.
