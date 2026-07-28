# Belletti OS — Cozinha 2.0

## O que foi implementado

- Kanban com colunas **Novos**, **Em preparo** e **Prontos**.
- Cartões com itens, observações, estação, instruções e checklist de preparo.
- Estações padrão: Cozinha, Bar, Cafeteria, Doces e Expedição.
- Filtro do painel por estação.
- Resumo consolidado “Produzir agora”.
- Cronômetro e classificação visual de atraso.
- Indicadores do dia: novos, preparo, prontos, entregues, tempo médio e atrasados.
- Histórico de mudanças de status.
- Atualização automática a cada 5 segundos quando houver mudança.
- Modo TV para exibição em tela grande.
- Cadastro de etapas de preparo dentro de cada prato no Django Admin.

## Arquivos alterados

- `cozinha/models.py`
- `cozinha/views.py`
- `cozinha/admin.py`
- `cozinha/urls.py`
- `templates/cozinha/painel.html`

## Arquivos novos

- `cozinha/migrations/0003_cozinha_2_0.py`
- `templates/cozinha/_pedido_card.html`

## Após subir para o GitHub

O Railway executará a migration pelo Procfile. Confirme nos logs:

```text
Applying cozinha.0003_cozinha_2_0... OK
```

Depois acesse:

```text
/cozinha/painel/
```

## Configuração necessária no Admin

Acesse:

```text
/admin/cozinha/prato/
```

Em cada prato, revise:

1. Estação responsável.
2. Tempo estimado de preparo.
3. Instruções rápidas.
4. Etapas de preparo do checklist.

Os novos pedidos passam a copiar as etapas do prato para o checklist, preservando o histórico mesmo se a receita for alterada depois.
