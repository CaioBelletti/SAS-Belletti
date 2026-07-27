# Mapeamento de funcionalidades — Olist vs sistema próprio

Registro de referência pra planejar as próximas fases, comparando a
estrutura de menus da Olist com o que já existe no sistema e o que
ainda falta construir.

## Cadastros

| Olist | Status no sistema próprio |
|---|---|
| Clientes e Fornecedores | Cliente já existe (`vendas`). Fornecedor ainda não — falta criar. |
| Produtos | Já existe (`catalogo.Produto`). |
| Categorias dos Produtos | Já existe (`catalogo.Categoria`). |
| Vendedores | Já existe via usuários/grupos do Django (grupos "Proprietário" e "Vendedores" que você já criou). |
| Embalagens | Não é prioridade agora — só relevante se passar a fazer envios. |
| Relatórios | Dashboard inicial já existe (`relatorios`). |

## Suprimentos

| Olist | Status no sistema próprio |
|---|---|
| Controle de Estoques | Já existe (`catalogo.MovimentacaoEstoque`). |
| Ordens de Compra | Não existe ainda — registraria a intenção de compra antes de virar Conta a Pagar. |
| Notas de Entrada | Não existe ainda — ligado a emissão fiscal, fica pra quando decidirmos como tratar nota fiscal. |
| Relatórios | Cobrível pelo dashboard, com adições. |

## Finanças

| Olist | Status no sistema próprio |
|---|---|
| Caixa | Já existe (`financeiro.MovimentoCaixa`). |
| Conta Digital / Crédito da Olist | Produtos bancários da própria Olist — não se aplicam a um sistema próprio. |
| Contas a Pagar | Já existe. |
| Contas a Receber | Já existe. |
| Cobranças Bancárias | Não existe — emissão de boleto/cobrança, fase futura se for necessário. |
| Extratos Bancários | Não existe — conciliação bancária automática, fase futura. |
| Relatórios | Cobrível pelo dashboard. |
| Painel de Contadores | Não é prioridade agora. |

## Dashboard (widgets vistos nos prints)

| Olist | Status no sistema próprio |
|---|---|
| Produtos mais vendidos | Já existe no dashboard atual. |
| Horários com mais vendas | Não existe ainda — fácil de adicionar (agrupar vendas por hora do dia). |
| Vendas x Devoluções | Não existe — depende de criar o conceito de devolução/estorno no sistema. |
| Funil de assuntos no CRM | Fora do escopo — é uma função de CRM/atendimento, não de PDV/financeiro. |

## Conclusão rápida

O que falta pra "empatar" com a Olist no essencial do dia a dia:
**Fornecedor**, **Ordem de compra**, **Horários com mais vendas** no
dashboard, e futuramente **Devoluções**. O resto (conta digital,
crédito, CRM) são produtos financeiros da própria Olist como empresa,
não fazem sentido pra replicar num sistema de gestão interna.
