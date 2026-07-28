# Cozinha 2.1 — Entrega na mesa e novos pedidos

## Alterações

- Adiciona o status `em_entrega` entre `pronto` e `entregue`.
- O cliente passa a receber a mensagem de que o pedido está sendo levado até a mesa.
- O painel da cozinha ganha a coluna **Em entrega**.
- O botão do pedido pronto muda para **Levar à mesa**.
- O pedido em entrega recebe o botão **Confirmar entrega**.
- A tela de acompanhamento ganha o botão **Fazer outro pedido nesta mesa**.
- O nome do cliente é lembrado no navegador para facilitar pedidos seguintes.

## Arquivos alterados

- `cozinha/models.py`
- `cozinha/views.py`
- `templates/cozinha/acompanhar.html`
- `templates/cozinha/cardapio.html`
- `templates/cozinha/painel.html`
- `templates/cozinha/_pedido_card.html`

## Arquivo novo

- `cozinha/migrations/0004_pedido_em_entrega.py`

## Deploy

```bash
git add cozinha templates/cozinha COZINHA_2_1_LEIA_ME.md
git commit -m "Adiciona entrega na mesa e novos pedidos"
git pull --rebase origin main
git push origin main
```

No Railway, confirme:

```text
Applying cozinha.0004_pedido_em_entrega... OK
```
