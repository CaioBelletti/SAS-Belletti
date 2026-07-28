# Belletti Cards Universe — PDV + Financeiro

Sistema próprio de PDV, controle de estoque e financeiro, feito em
Django. Substitui o Olist como ferramenta de gestão do dia a dia.

## O que já está pronto (Fase 1)

- **Catálogo/estoque**: cadastro de produtos (cartas) com SKU, raridade,
  edição, estado de conservação, preço de custo/venda e estoque.
  Toda entrada/saída de estoque fica registrada em histórico.
- **Vendas (PDV)**: uma venda é aberta, recebe itens, e ao ser
  **fechada** o sistema automaticamente:
  1. Confere se há estoque suficiente (bloqueia se não houver)
  2. Baixa o estoque de cada item vendido
  3. Cria a conta a receber (já marcada como recebida se for pagamento
     à vista: dinheiro, Pix, débito ou crédito à vista)
  4. Lança a entrada no caixa (se à vista)
  Tudo isso numa única transação — se algo falhar no meio, nada é
  salvo pela metade.
- **Financeiro**: contas a pagar, contas a receber, movimentos de
  caixa e categorias financeiras (a base pro DRE).
- **Painel administrativo pronto** (`/admin`) — é onde você vai
  cadastrar produtos, registrar vendas e gerenciar o financeiro
  enquanto ainda não construímos as telas customizadas do PDV.
- **3 testes automatizados** garantindo que essa integração funciona.

- **Cliente completo**: endereço (CEP, logradouro, bairro, cidade,
  UF) e data de nascimento no cadastro. Widget de **aniversariantes
  do mês** no dashboard, com destaque pra quem faz aniversário hoje.
- **Blacklist de cliente**: marque um cliente problemático (ex:
  cheque sem fundo) e o PDV mostra um aviso vermelho na hora de
  selecionar ele numa venda — não bloqueia a venda, só alerta o
  vendedor.
- **LGPD**: campo de consentimento de uso de dados, e uma ação no
  admin ("Anonimizar dados pessoais") que implementa o direito ao
  esquecimento — apaga nome, telefone, e-mail, documento e endereço,
  mas **mantém o histórico financeiro** (total gasto, número de
  compras), já que isso tem obrigação de retenção separada dos dados
  pessoais em si.
- **Indicadores financeiros**: novo widget no dashboard com margem
  bruta %, margem líquida %, CMV sobre receita, despesas sobre
  receita, e ponto de equilíbrio (quanto precisa faturar no mês pra
  cobrir as despesas, considerando a margem atual).
- **Fluxo de caixa completo**: widget novo no dashboard com abas
  (Diário/Semanal/Mensal/Anual) mostrando entradas x saídas de
  verdade lado a lado — diferente dos gráficos de receita que já
  existiam, esse pega todo o caixa (vendas, sangrias, suprimentos,
  tudo).
- **Bancos** (menu Cadastros → "Bancos e conciliação"): cadastre suas
  contas bancárias, importe o extrato em **OFX** (o formato que
  praticamente todo banco disponibiliza pra download), e concilie
  contra os lançamentos do sistema — automaticamente quando o valor e
  a data batem, ou manualmente pelo admin quando não bate. Não emite
  boleto nem PIX automático de verdade (isso exige conta num gateway
  de pagamento), mas o controle e a conciliação já funcionam.
- **Parcelamento real**: uma venda parcelada no PDV agora gera
  parcelas de verdade (contas a receber separadas, uma pra cada mês),
  em vez de um valor único. Também dá pra lançar uma conta a pagar ou
  a receber parcelada manualmente em **Finanças → "Lançar conta
  parcelada"** — informe o valor total e o número de parcelas, o
  sistema divide certinho (com a diferença de arredondamento jogada
  na última) e escalona os vencimentos de 30 em 30 dias.
- **Recorrência automática de verdade**: contas a pagar marcadas como
  "recorrente" agora geram sozinhas a próxima ocorrência (1 mês
  depois) assim que você marca a atual como paga — sem precisar
  recadastrar todo mês.
- **Meio de pagamento categorizado**: contas a pagar e a receber agora
  têm um campo específico pra Pix, Boleto, TED, DOC, Transferência
  bancária, Cartão, Dinheiro ou Cheque — dá pra filtrar e saber como
  o dinheiro entrou/saiu.
- **Controle de boleto** (sem emitir de verdade): campos pra guardar
  o número do boleto e a linha digitável, pra referência — se você
  gerar o boleto em outro lugar (banco, PagSeguro, etc), só cola a
  linha digitável aqui pra manter tudo num lugar só.
- **Conferência de recebimento com backorder**: ao receber uma ordem
  de compra, confira quantidade por quantidade contra o que
  realmente chegou. Se vier menos que o pedido, o restante fica em
  aberto como "backorder" — você pode voltar depois e registrar o
  resto assim que chegar, e cada entrega parcial já lança sua própria
  conta a pagar. A ordem só fecha quando tudo tiver chegado.
- **Cotações**: peça preço a vários fornecedores pros mesmos
  produtos, compare lado a lado (o menor preço já vem destacado), e
  gere a(s) ordem(ns) de compra automaticamente a partir do
  fornecedor escolhido por item.
- **Análise de compras**: preço médio pago por produto (com o menor
  preço já conseguido), e ranking de fornecedores por valor total
  comprado e atraso médio de entrega.
- **Perdas e quebras categorizadas** (menu Cadastros → "Perdas e
  quebras"): registra baixa de estoque por perda, quebra, dano,
  roubo ou vencimento, com resumo mensal por categoria (quanto em R$
  cada motivo representou).
- **Giro e cobertura de estoque**: novo widget no dashboard mostrando,
  por produto, quantas vezes o estoque "virou" nos últimos 90 dias
  (giro) e quantos dias o estoque atual deve durar no ritmo de venda
  recente (cobertura) — ajuda a ver o que gira rápido e o que está
  parado antes mesmo de virar alerta de "produto parado".
- **Reservas** (menu Cadastros → "Reservas"): segure estoque pra um
  cliente sem finalizar a venda ainda. O estoque "reservado" não
  aparece mais como disponível pra vender (o PDV mostra os dois
  números quando são diferentes), evitando vender o que já tem dono.
- **Inventário/Conferência** (menu Cadastros → "Inventário /
  Conferência"): abre uma sessão de contagem física (de todos os
  produtos ou só de uma categoria), mostra o que o sistema espera
  encontrar de cada item, você digita o que contou de verdade, e ao
  finalizar o sistema ajusta o estoque automaticamente só onde houve
  diferença — sem mexer no que não foi contado. Fica um histórico das
  últimas conferências, com quantas divergências cada uma teve.
- **Cadastro de produto completo**: código interno, EAN, marca,
  fornecedor padrão, subcategoria, tags, idioma, descrição, imagem,
  peso e dimensões, estoque máximo, localização física, lote,
  validade, número de série, frete e impostos embutidos no custo, e
  preço mínimo de venda. Margem, lucro e markup agora consideram
  custo + frete + impostos juntos (não só o preço de custo puro).
  **Atenção**: imagens de produto ficam salvas no disco local — no
  Railway, isso se perde a cada redeploy (o disco lá é temporário).
  Funciona sem problema rodando local; pra produção de verdade, o
  ideal seria um serviço externo de armazenamento (fora do escopo
  atual).
- **Produtos compostos** (Kit, Combo, Bundle, Booster Box, Blister,
  ETB, Case): cadastre os componentes na ficha do produto composto
  (seção "Componentes"), depois use "Composição (kits/combos/booster
  box)" no menu Cadastros pra **desmontar** (abrir o composto em
  itens individuais) ou **montar** (juntar itens individuais em um
  composto) — ambos ajustam o estoque de tudo automaticamente.
- **Desconto por item, acréscimo e observações**: no PDV, cada item
  do carrinho tem seu próprio campo de desconto, além do desconto
  geral da venda. Também dá pra adicionar um acréscimo (R$) e uma
  observação de texto livre — tudo fica salvo na venda.
- **Cashback e crédito do cliente**: configurável em Vendas →
  Configuração de fidelidade (% do valor da compra vira crédito
  automático). No PDV, ao selecionar um cliente com saldo, aparece a
  opção de usar esse crédito como desconto na hora.
- **Cupom de desconto**: crie cupons (percentual ou valor fixo, com
  validade e limite de usos) em Vendas → Cupons de desconto. No PDV,
  digite o código e clique em "Aplicar" — o sistema valida e mostra
  o desconto calculado antes de finalizar.
- **Vale (voucher)**: crie vales com saldo próprio em Vendas → Vales.
  No PDV, "Vale" é uma forma de pagamento — digite o código, consulte
  o saldo disponível, e o valor usado é debitado automaticamente do
  vale ao fechar a venda.
- **Orçamento**: no PDV, "Salvar como orçamento" monta a mesma venda
  mas sem tocar em estoque ou financeiro — é só uma cotação. Depois,
  no admin (Vendas → Vendas), a ação "Converter orçamento em venda
  aberta" transforma num pedido de verdade, pronto pra fechar.
- **Grading/autenticidade**: no cadastro de produto, campos pra
  registrar empresa de grading (PSA, BGS, CGC, SGC), nota e número do
  certificado — aparece destacado no admin e na busca do PDV.
- **Autenticação em duas etapas (2FA)**: qualquer usuário pode ativar
  em "Segurança (2FA)" na barra lateral — escaneia um QR code com um
  app autenticador (Google Authenticator, Authy, Microsoft
  Authenticator) e confirma com um código. Depois disso, o login
  passa a exigir usuário+senha **e** o código do app.
- **Bloqueio por tentativas de login**: depois de 5 tentativas
  erradas (de senha ou de código 2FA) em 15 minutos, o login fica
  bloqueado por 15 minutos — proteção contra tentativa de adivinhar
  senha por força bruta.
- **Produtos parados**: no dashboard, lista produtos com estoque
  disponível que não vendem há X dias (padrão 60, configurável em
  Relatórios → "Configuração de estoque"). Produtos recém-cadastrados
  ganham um período de graça, não aparecem como "parados" de cara.
- **Sugestão de preço por margem**: no cadastro de produto, preencha
  "Margem desejada (%)" e o preço de venda é calculado sozinho a
  partir do preço de custo, ao digitar — você pode ajustar
  manualmente depois se quiser.
- **Fidelidade e histórico de compras**: cliente ganha pontos
  automaticamente a cada compra fechada (configurável em Vendas →
  "Configuração de fidelidade" — padrão é 1 ponto a cada R$ 10
  gastos, cada ponto vale R$ 0,10 de desconto). No PDV, ao selecionar
  um cliente com pontos, aparece a opção de resgatar parte deles como
  desconto na hora. Uma devolução desconta pontos proporcionalmente.
  Na ficha do cliente (`/admin/vendas/cliente/`) você vê o saldo de
  pontos, total gasto, número de compras, e o histórico completo de
  vendas dele.
- **Notificações automáticas**: alertas por e-mail (e opcionalmente
  WhatsApp) quando o estoque de um produto fica baixo, quando a
  diferença no fechamento de caixa passa de um limite configurado, e
  um resumo diário (contas vencendo, estoque baixo, status da meta)
  via o comando `python manage.py verificar_alertas` — agendável
  igual o backup. Configure o destino em Configuração → "Configuração
  de notificações" no admin.
  - **E-mail**: funciona de graça — defina `EMAIL_HOST`,
    `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` nas variáveis de
    ambiente (funciona com Gmail usando senha de app, SendGrid, etc).
    Sem configurar nada, os e-mails só aparecem no console/log — bom
    pra testar sem gastar nada.
  - **WhatsApp**: opcional e pago — precisa de uma conta Twilio
    própria. Defina `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` e
    `TWILIO_WHATSAPP_FROM` nas variáveis de ambiente. Sem isso
    configurado, o sistema simplesmente não manda WhatsApp (não dá
    erro).
- **Etiquetas com código de barras** (menu Cadastros → "Etiquetas com
  código de barras"): selecione produtos sem código de fábrica, o
  sistema gera um código próprio (Code128) e uma folha pronta pra
  imprimir e colar no produto — depois disso, o leitor de código de
  barras já reconhece normalmente no PDV.
- **Exportar dashboard pra Excel** (botão no topo do dashboard):
  baixa um `.xlsx` com resumo, vendas por mês, DRE, curva ABC,
  comissões e próximos vencimentos — pronto pra levar pro contador.
- **Canal de venda**: cada venda no PDV é marcada como "loja física"
  ou "online", pra você comparar depois quando reabrir a loja física.
- **Múltiplos caixas simultâneos**: cada vendedor pode abrir seu
  próprio caixa independente — útil quando tiver mais de um caixa
  registrador funcionando ao mesmo tempo.
- **Backup**: botão "Baixar backup agora" na barra lateral (só pra
  quem tem acesso staff) baixa um arquivo `.json` com todos os dados
  na hora. Pra automatizar, existe também o comando
  `python manage.py backup_dados`, que salva em `backups/` e mantém
  só os 10 mais recentes — dá pra agendar (Agendador de Tarefas do
  Windows local, ou um cron job no Railway) pra rodar todo dia.
- **Log de auditoria**: "Log de auditoria" na barra lateral mostra
  quem fez o quê — vendas fechadas, caixa aberto/fechado, sangria/
  suprimento, devolução processada, ordem de compra recebida — com
  usuário e horário.
- **Comissão de vendedor**: no dashboard, mostra quanto cada vendedor
  vendeu no mês e a comissão calculada, com base no percentual
  configurado em Vendas → "Perfis de vendedor" (crie um pra cada
  usuário que vende).
- **Curva ABC de produtos**: no dashboard, classifica os produtos em
  A (que juntos somam até 80% do faturamento), B (até 95%) e C (o
  resto) — ajuda a ver quais produtos realmente sustentam o negócio.
- **Permissões**: existem dois níveis de acesso — usuários com "acesso
  staff" marcado (dono/gerência) veem tudo, incluindo o dashboard
  financeiro e o `/admin`. Usuários sem acesso staff (vendedores) só
  conseguem usar o **PDV** e o **Caixa** — não veem faturamento, DRE,
  nem o painel administrativo. Pra marcar/desmarcar isso, edite o
  usuário em `/admin/auth/user/` e ajuste a caixinha "Membro da
  equipe" (equivale a `is_staff`).
- **Caixa** (menu lateral → "Caixa", disponível pra qualquer usuário
  logado): abrir o turno com um valor de troco, registrar sangria
  (retirar dinheiro) e suprimento (reforçar), e fechar conferindo o
  valor contado contra o saldo esperado pelo sistema — mostra a
  diferença automaticamente. Só pode haver um caixa aberto por vez.
- **Pagamento misto**: no PDV, dá pra dividir uma venda em mais de uma
  forma de pagamento (ex: metade no dinheiro, metade no pix) — o
  sistema só libera "Finalizar" quando a soma dos pagamentos bate
  exatamente com o total da venda.
- **Informativos do dashboard**: contador de produtos diferentes em
  catálogo, barra de progresso da meta de faturamento do mês (defina
  a meta em Finanças → "Metas mensais"), e lista de produtos que
  precisam de reestoque (estoque atual abaixo do mínimo configurado).
- **Importação de estoque** (menu Suprimentos → "Importar estoque"):
  envie um print da tela, PDF ou `.txt` do fornecedor mostrando nome,
  quantidade e valor de cada item. O sistema tenta reconhecer os itens
  automaticamente (OCR pra imagem, leitura de texto pra PDF/txt), te
  mostra uma tela de conferência pra corrigir o que saiu errado, e só
  então cria uma Ordem de compra em aberto — nada entra no estoque/
  financeiro até você revisar e clicar em "Receber" no admin.
- **Leitor de código de barras**: cadastre o código EAN/UPC de fábrica
  no campo "Código de barras" do produto (tela Produtos). No PDV,
  escaneie normalmente — o leitor USB funciona como teclado, então ao
  ler o código e mandar "Enter" sozinho, o produto já cai direto no
  carrinho, sem precisar clicar em nada. A busca manual por nome/SKU
  continua funcionando do mesmo jeito.
- **PDV** (`/pdv/`): tela de venda rápida — busca produto por nome/SKU,
  monta carrinho, aplica desconto, escolhe forma de pagamento e
  finaliza a venda com um clique (baixa estoque e lança financeiro
  automaticamente, tudo em uma transação — se algo falhar, nada é
  salvo pela metade).
- **Devoluções**: registre uma devolução (total ou parcial) de uma
  venda já fechada pelo admin. Ao processar, o sistema devolve o
  estoque e estorna o valor certo — saída de caixa se a venda já
  tinha sido recebida, ou redução/cancelamento da conta a receber se
  ainda estava pendente. Bloqueia devolver mais do que foi vendido.
- **Fluxo de caixa projetado**: no dashboard, gráfico com a projeção
  de saldo dos próximos 30 dias (saldo atual + contas a receber
  pendentes − contas a pagar pendentes, dia a dia), mais uma lista
  dos próximos vencimentos.
- **DRE simplificado**: no dashboard, demonstrativo do mês atual —
  receita bruta, devoluções, CMV (custo da mercadoria vendida),
  margem bruta, despesas operacionais e lucro líquido.
- **Suprimentos**: cadastro de fornecedores e ordens de compra. Ao
  marcar uma ordem como "recebida" (ação no admin), o sistema
  automaticamente dá entrada no estoque de cada item e cria a conta
  a pagar pro fornecedor.
- **Dashboard de vendas** (acesse a raiz do site, `/`, logado): total
  de vendas, ticket médio, saldo em caixa, gráfico de vendas por mês,
  produtos mais vendidos e horários com mais vendas.

## O que falta (próximas fases, veja o roadmap que combinamos)

- Integração com a API do Olist pra importar seu catálogo/estoque atual

## Fora de escopo (decisão consciente, não vamos construir)

- Emissão de NF-e/NFC-e
- Impressão de recibo/cupom não fiscal

## OCR (leitura de prints) — Tesseract

A importação de estoque por print de tela usa o **Tesseract OCR**,
que é um programa separado do Python (não vem incluso no
`requirements.txt`).

**No Railway**: já está resolvido — o arquivo `nixpacks.toml` instrui
o Railway a instalar o Tesseract automaticamente no deploy. Você não
precisa fazer nada.

**Rodando localmente no Windows**: baixe o instalador em
https://github.com/UB-Mannheim/tesseract/wiki e instale normalmente.
Se o `iniciar.bat` não achar o Tesseract sozinho, defina o caminho
dele numa variável de ambiente antes de rodar (ajuste conforme o
caminho da sua instalação):

```
set TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

Importação de PDF e `.txt` funciona sem o Tesseract — só o OCR de
imagem depende dele.

## Rodando localmente (jeito automático — Windows)

Só precisa ter o [Python instalado](https://www.python.org/downloads/)
(na instalação, marque "Add Python to PATH").

Dê **duplo-clique em `iniciar.bat`**. Na primeira vez ele vai:
1. Criar o ambiente virtual
2. Instalar as dependências
3. Aplicar as atualizações no banco de dados
4. Pedir pra você criar seu usuário administrador (só na primeira vez)
5. Abrir o sistema automaticamente no navegador

Nas próximas vezes, é só dar duplo-clique de novo — ele pula as
etapas que já foram feitas e sobe o sistema direto. Pra parar, feche
a janela preta ou aperte `Ctrl+C`.

## Rodando localmente (manual — Mac/Linux ou se preferir por comando)

Pré-requisitos: Python 3.11+.

```bash
# 1. Entre na pasta do projeto
cd belletti_pdv

# 2. Crie um ambiente virtual (isola as dependências do projeto)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Aplique as migrações (cria as tabelas no banco)
python manage.py migrate

# 5. Crie seu usuário de administrador
python manage.py createsuperuser

# 6. Rode o servidor local
python manage.py runserver
```

Acesse `http://127.0.0.1:8000/admin` e faça login. Localmente o
sistema usa SQLite automaticamente — não precisa instalar banco nenhum.

Pra rodar os testes automatizados a qualquer momento:

```bash
python manage.py test
```

## Publicando no Railway

1. Suba este projeto pra um repositório no GitHub (o Railway conecta
   direto com GitHub).
2. No Railway, crie um novo projeto a partir desse repositório.
3. Adicione um serviço **PostgreSQL** ao projeto (botão "+ New" →
   "Database" → "PostgreSQL"). O Railway cria a variável
   `DATABASE_URL` sozinho e o sistema já está configurado pra
   detectar isso automaticamente.
4. Nas variáveis de ambiente do serviço web, adicione:
   - `SECRET_KEY` — gere uma string aleatória longa (não repita a de
     desenvolvimento)
   - `DEBUG` = `False`
5. O Railway vai detectar o `Procfile` e rodar automaticamente:
   migração do banco → coleta de arquivos estáticos → subir o
   servidor com Gunicorn.
6. Depois do primeiro deploy, crie o superusuário direto no Railway
   (aba "Shell" do serviço, ou via `railway run python manage.py
   createsuperuser`).

## Dashboard: mais funcionalidades recentes

- **Dashboard personalizável (arrastar-e-soltar)**: clique em
  "Personalizar dashboard" no topo — cada seção vira um bloco que
  você pode arrastar pela alça (⋮⋮) pra reordenar, ou clicar em
  "Ocultar"/"Mostrar" pra esconder o que não usa. Salva sozinho, por
  usuário. Os cards de métrica do topo ficam sempre fixos.
- **Central de alertas**: junta contas vencidas, estoque crítico,
  produtos parados, meta em risco e diferença de caixa num só lugar.
- **Heatmap de vendas**: matriz de dia da semana × horário, cor mais
  forte onde há mais vendas concentradas.
- **Pedidos em andamento**: mostra vendas que ficaram "abertas"
  (criadas mas não finalizadas), com alerta se ficarem esquecidas.
- **Comparação mensal/anual**, **gráfico de lucro histórico**,
  **receita diária/semanal** e **produtos menos vendidos** também
  fazem parte do dashboard agora.

## Central de Relatórios (menu "Relatórios", separado do dashboard)

- **Vendas por categoria**: quantidade, receita, margem e % do total
  por categoria de produto, últimos 12 meses.
- **Top clientes**: ranking por total gasto, número de compras e
  ticket médio individual.
- **Análise XYZ**: classifica cada produto por previsibilidade de
  demanda (X = constante, Y = variável, Z = esporádica), usando o
  coeficiente de variação das vendas mensais — complementa a curva
  ABC (que é por valor) com a dimensão de regularidade.
- **Devoluções**: total no período, valor devolvido, e ranking dos
  motivos mais comuns.
- **Desempenho por vendedor**: número de vendas, itens vendidos,
  total vendido e ticket médio de cada vendedor.

## Estoque por carta — os itens rápidos

- **Preço máximo**: campo novo, ao lado do preço mínimo que já
  existia — referência de teto pra cartas com preço volátil.
- **Preço médio de venda**: calculado automaticamente a partir do
  que foi vendido de verdade (não é o preço de tabela) — aparece na
  ficha do produto.
- **Histórico de preço**: toda vez que o preço de venda de um
  produto muda, fica registrado sozinho (data, valor antigo, valor
  novo) — visível na própria ficha do produto, sem precisar fazer
  nada manualmente.

**Ainda pendente dessa lista** (Deck Builder e Liga, que você
confirmou querer): são dois módulos grandes, cada um do tamanho de
um produto à parte — Deck Builder precisa de validação de
legalidade por formato pra 5 jogos diferentes, e Liga precisa de um
sistema de pareamento suíço, check-in e chaveamento. Fica pra uma
sessão dedicada só pra planejar a arquitetura de cada um antes de
começar a construir. **Compra Inteligente** (CardMarket/TCGPlayer)
segue na mesma fila de "burocracia" do LigaMagic — precisa de conta
de parceiro aprovada nessas plataformas.

## Aplicativo Mobile (PWA) — item 19

O sistema virou um **PWA (Progressive Web App)** — instalável direto
do navegador do celular, sem precisar de loja de aplicativo.

- **Instalar**: abra o site no Chrome/Safari do celular e use
  "Adicionar à tela inicial" — vira um ícone que abre em tela cheia,
  como um app de verdade.
- **Leitor de código de barras pela câmera**: botão de câmera ao
  lado da busca do PDV, usando a câmera do celular (sem precisar de
  leitor físico).
- **Notificações push**: clique em "Ativar notificações" na
  sidebar — você passa a receber alertas urgentes (ex: backup
  atrasado, estoque zerado) direto no celular, mesmo com o app
  fechado. Isso já roda junto com `rodar_automacoes_crm`.
- **Modo offline com venda de verdade**: se a internet cair no meio
  do expediente, o PDV continua funcionando — a venda é salva no
  próprio aparelho e sincronizada sozinha assim que a conexão
  voltar. A busca de produto também funciona offline, usando uma
  cópia local do catálogo baixada automaticamente enquanto há
  internet.
  - **Sobre o risco de conflito** (que você aceitou conscientemente):
    se duas vendas offline consumirem o mesmo estoque enquanto
    ambas estavam offline, ao sincronizar o sistema **não corrompe
    nada automaticamente** — a venda que não couber no estoque fica
    registrada em **Admin → Vendas → Vendas offline pendentes**,
    esperando você decidir manualmente (ajustar, cancelar, ou
    liberar estoque negativo conscientemente).

## BI Avançado (menu "BI Avançado")

- **Filtros combinados**: período, categoria e vendedor, tudo junto
  numa tela só.
- **Drill-down**: a tabela mostra o item de venda individual, não só
  o número agregado — dá pra ver exatamente quais vendas compõem
  aquele total.
- **Mapa de clientes por estado** (Leaflet + OpenStreetMap, sem
  chave de API nenhuma) — tamanho do círculo mostra quantos clientes
  vêm de cada UF.
- **Exportação em CSV e PDF**, além do Excel que já existia.
- **Conexão direta com Power BI**: o sistema cria views SQL prontas
  (`vw_bi_vendas`, `vw_bi_itens_venda`, `vw_bi_estoque`,
  `vw_bi_financeiro`) já com os dados juntos e legíveis, pra você
  conectar o Power BI Desktop direto no banco (Obter dados → Banco
  de dados PostgreSQL) sem precisar de nenhuma API extra. Rode
  `python manage.py criar_usuario_powerbi` (só funciona no
  PostgreSQL/Railway, não local) pra gerar um usuário **somente
  leitura** — o Power BI nunca tem permissão de escrita no seu banco.

## Refino visual — identidade consistente em todo o sistema

Refinamos a identidade que a Belletti já tinha (fundo escuro,
roxo como cor de ação, dourado como assinatura, brilho "foil"
holográfico nos botões — uma referência ao próprio produto) pra
ficar consistente em lugares que ainda destoavam:

- **Admin do Django recolorido**: todas as telas de cadastro
  (Produto, Categoria, Fornecedor, Contas, etc.) agora usam a mesma
  paleta do resto do sistema, em vez do azul padrão do Django —
  sobrescrevendo as variáveis de tema que o próprio admin usa, então
  praticamente toda superfície (tabelas, formulários, botões,
  mensagens) herdou o visual de graça.
- **Cardápio público e acompanhamento do pedido reconstruídos**:
  agora usam exatamente as mesmas fontes, cores e o brilho "foil" de
  assinatura do resto do sistema, em vez de uma paleta aproximada.
- **Mensagens de sucesso/erro padronizadas**: consolidamos 9 lugares
  diferentes que redefiniam a mesma caixinha de mensagem (com
  variações sutis) numa única definição compartilhada em `app.css`.

## Auditoria final antes do Railway

- **Endurecimentos de segurança de produção**: HTTPS obrigatório,
  cookies de sessão/CSRF marcados como seguros, e HSTS ativado —
  tudo isso só entra em vigor com `DEBUG=False` (não afeta o uso
  local). Rodei `python manage.py check --deploy` com uma
  `SECRET_KEY` de verdade: **zero avisos**.
- **`.gitignore` revisado** — reforçado com entradas de ambiente
  virtual, IDE e arquivos de sistema, além do que já cobria
  (`db.sqlite3`, `media/`, `backups/`, `.env`).
- **`requirements.txt` conferido**: escaneei todos os imports do
  código inteiro e confirmei que cada biblioteca externa usada está
  listada (ou vem junto como dependência de outra, como o
  `py-vapid` que já vem com o `pywebpush`).
- **`collectstatic` testado de verdade** — é o comando que o Railway
  roda automaticamente antes de subir; confirmei que processa os
  139 arquivos estáticos sem erro.

## Belletti Menu — mesas, comandas e fechamento pelo PDV

Evolução do cardápio digital, seguindo o MVP: mesas com QR code
próprio, comanda por mesa, chamar atendente, e fechamento gerando
uma venda de verdade no financeiro.

- **Mesa com token imprevisível**: cada mesa tem um UUID no QR code
  (não o número em texto puro), pra não dar pra forjar trocando um
  número na URL. Cadastre em Admin → Cozinha → Mesas.
- **Confirmação antes do pedido**: ao ler o QR, a primeira tela
  pergunta "Você está na Mesa 07?" — evita pedido feito com foto de
  QR antigo.
- **Comanda por mesa**: os pedidos de uma mesa se acumulam numa
  comanda só, com o total certo, até fechar.
- **Chamar atendente**: botão no cardápio da mesa, aparece na hora
  no painel da cozinha com destaque.
- **Fechamento pelo PDV**: tela "Mesas abertas" mostra o consumo
  de cada mesa — ao fechar, gera uma Venda de verdade (aparece no
  financeiro/DRE normalmente).
- **Proteções**: pedido duplicado (clique duplo) é bloqueado por 5
  segundos; IP e dispositivo ficam registrados em cada pedido;
  mesa pode ser pausada (não aceita pedido) sem apagar o cadastro.
- **QR codes pra imprimir**: Admin → Cozinha → Mesas → link de QR
  individual, ou baixe um PDF pronto com todas as mesas de uma vez
  (Painel da cozinha → topo).

**Ficou de fora por decisão consciente (fase 2, como definido)**:
pagamento por PIX direto no celular do cliente, divisão de conta,
adicionais com preço extra (só observação em texto por enquanto),
cupom/fidelidade no cardápio, WebSockets (o painel atualiza por
polling a cada 20s, que é suficiente pro volume esperado), e
horários dinâmicos de cardápio.

## Preenchimento automático de endereço pelo CEP

Na ficha de Cliente (Admin), assim que você termina de digitar o CEP
(8 dígitos), o sistema busca sozinho no **ViaCEP** (gratuito, sem
chave de API, sem cadastro) e preenche logradouro, bairro, cidade e
UF automaticamente — só o número e o complemento ficam por sua
conta. Se o CEP não existir ou a internet cair no meio, nada quebra:
os campos simplesmente ficam vazios pra preencher manualmente, como
antes. Campos que você já tiver preenchido manualmente não são
sobrescritos.

## Módulo de Cozinha (cardápio digital + painel da cozinha)

Novo módulo pra um cantinho de lanches/café dentro da própria loja.

- **Cardápio digital** (`/cardapio/`) — tela sem login, pensada pra
  ser acessada via QR code impresso na mesa/balcão. Cliente monta o
  pedido (foto, descrição e preço de cada prato), informa o nome e
  a mesa, e envia — sem precisar baixar nada nem se cadastrar.
- **Acompanhamento do pedido**: depois de enviar, o cliente cai numa
  tela própria (link único) que mostra o status em tempo real
  (Recebido → Em preparo → Pronto → Entregue), atualizando sozinha.
- **Painel da cozinha** (menu "Cozinha", staff): pedidos ordenados
  por prioridade (Normal/Alta/Urgente) e depois por horário de
  chegada. Um clique avança o status; dá pra mudar a prioridade ou
  cancelar. Atualiza sozinho a cada 20 segundos.
- **QR code pronto**: botão no painel que gera e baixa a imagem do
  QR code apontando direto pro cardápio — é só imprimir e colar na
  mesa/balcão.
- **Cadastro de pratos** (Admin → Cozinha → Pratos): nome, descrição,
  preço, foto, categoria, disponibilidade e tempo estimado de
  preparo.
- Esse módulo tem sua própria área de permissão ("Cozinha / Cardápio")
  — por padrão nenhum perfil restrito tem acesso automático, você
  libera em Admin → Grupos pra quem precisar.

## Aprovação em múltiplos níveis (item 20 — "Belletti OS Enterprise")

Do pacote "Enterprise" você escolheu construir isso primeiro — o
resto (multiempresa/multi-loja) ficou marcado como visão de futuro,
já que exigiria redesenhar a base de dados inteira.

- **Configuração** (Admin → Aprovações → Regras de aprovação): pra
  cada tipo (Compra, Pagamento, Desconto no PDV), defina um valor
  limite e uma cadeia de níveis — cada nível é um Grupo/perfil
  (ex: nível 1 = Gerente, nível 2 = Financeiro). Precisa passar por
  todos os níveis em sequência pra ser liberado; rejeitar em
  qualquer nível encerra tudo na hora.
- **Compras**: ordem de compra acima do limite (reposição automática
  ou manual) fica "aguardando aprovação" em vez de liberar direto.
- **Pagamentos**: marcar uma conta a pagar como paga é bloqueado e
  revertido automaticamente se precisar de aprovação — só vira
  "pago" de verdade depois de aprovado.
- **Desconto no PDV**: venda com desconto acima do limite não fecha
  na hora — fica pendente, sem mexer no estoque, até ser aprovada.
- **Tela "Aprovações"** (sidebar): quem tem o perfil certo aprova ou
  rejeita, com comentário opcional. Mostra histórico das últimas 20
  decisões.

## Módulo TCG — cadastro de carta completo

Além do que já existia (Idioma, Coleção/Edição, Raridade, Condição,
Grading com PSA/BGS/CGC/SGC), agora também tem:

- **Número na coleção** (ex: "025/198", o número impresso na carta)
- **Foil**, **Reverse Holo** e **Promo** — checkboxes próprios, não
  mais escondidos dentro do campo de raridade como texto livre
- Tudo isso é filtrável e pesquisável no admin, e aparece resumido
  (ex: "Foil · Promo") na busca do PDV, ao lado do grading

## Inteligência (menu "Inteligência") — item 16 da sua lista

Tudo aqui é **estatística e regras de negócio sobre os seus próprios
dados** — não usa nenhuma IA generativa/paga. Se um dia você quiser
"insights" em texto corrido de verdade (tipo um analista explicando
os números), isso exigiria plugar uma API de IA (Anthropic/OpenAI,
com custo por uso) — fica registrado como próximo passo natural.

**IA Financeira**: previsão de faturamento e lucro do próximo mês
(por tendência dos últimos meses), capital de giro, e sugestão de
margem/preço por produto (heurística: produto que gira rápido pode
ter margem menor, produto parado sugere margem maior).

**IA Estoque**: capital parado (quanto está imobilizado em produtos
sem giro), lista de ruptura iminente (menos de 15 dias de estoque)
e excesso de estoque (mais de 180 dias de cobertura).

**IA Comercial**: clientes inativos (90+ dias sem comprar), chance
de recompra (compara o intervalo médio de compras de cada cliente
com quanto tempo já passou desde a última), e cross-selling
(produtos frequentemente comprados juntos na mesma venda).

**IA Gerencial**: insights automáticos (frases geradas a partir de
comparações — queda/alta de vendas, margem apertada, capital de
giro negativo, pedidos parados), e os resumos automáticos por
e-mail agora têm 4 frequências (diário/semanal/mensal/anual,
configurável em Relatórios → Configuração de relatório automático).

Também nessa rodada: **recuperação de carrinho** — se um pedido
fica em aberto por tempo demais (padrão 3h) e tem cliente
identificado com telefone/e-mail, manda uma mensagem perguntando se
ainda tem interesse (Admin → CRM → Configuração do CRM).

## Automações: cobrança, reposição e relatório periódico

Todas rodam junto com `python manage.py rodar_automacoes_crm` (o
mesmo comando das automações do CRM — agende ele pra rodar 1x por
dia e todas as automações do sistema disparam sozinhas).

- **Cobrança automática** (Admin → Financeiro → Configuração de
  cobrança): manda WhatsApp/e-mail pro cliente quando uma conta a
  receber vence, respeitando um intervalo mínimo entre cobranças da
  mesma conta (padrão 7 dias, pra não spammar).
- **Reposição automática de estoque** (Admin → Relatórios →
  Configuração de estoque): quando um produto bate no estoque
  mínimo, gera a ordem de compra sozinho pro fornecedor padrão dele
  — a quantidade sugerida usa o "estoque máximo" se estiver
  definido, ou um múltiplo do mínimo como alternativa. Não duplica
  ordem se já existir uma aberta com aquele produto.
- **Relatório periódico por e-mail** (Admin → Relatórios →
  Configuração de relatório automático): manda um resumo (vendas,
  ticket médio, lucro, alertas ativos) semanalmente (toda
  segunda-feira) ou mensalmente (todo dia 1º), sem duplicar envio no
  mesmo dia.

## Segurança: backup, criptografia e proteção de borda

- **Aviso de backup atrasado**: a Central de Alertas do dashboard
  agora avisa se faz mais de 3 dias sem um backup novo (seja manual
  ou automático) — e fica urgente se passar de 6 dias.
- **Criptografia em repouso**: o CPF/CNPJ de clientes e fornecedores
  agora fica **criptografado no banco de dados** (AES via Fernet) —
  mesmo que alguém tenha acesso direto ao arquivo do banco, não
  consegue ler esses dados sem a chave. Continua transparente no
  Django (você vê o valor normal na tela), só o que fica gravado
  fisicamente é que vira texto ilegível. Dado que já existia antes
  dessa mudança continua funcionando normalmente.
- **Bloqueio manual de IP** (Admin → Segurança → IPs bloqueados):
  adicione um IP problemático e toda requisição vinda dele é
  recusada na hora.
- **Rate limit geral**: qualquer IP fazendo mais de 180 requisições
  por minuto no sistema leva um "muitas requisições, tente de novo"
  — proteção básica contra varredura automatizada, sem atrapalhar o
  uso normal do dia a dia.

## Usuários: perfis, sessões e auditoria

- **Perfis nomeados** (Admin → Autenticação e autorização → Grupos):
  já vêm 4 perfis prontos — **Gerente** (acesso total), **Vendedor**
  (só PDV e Caixa), **Financeiro** (Financeiro e Relatórios) e
  **Estoquista** (Catálogo e Suprimentos). Pra criar um perfil novo
  ou mudar o que um perfil vê, edite o Grupo no admin — a seção
  "Perfil de acesso" dentro dele mostra as áreas do sistema
  (checkboxes) que aquele perfil pode acessar. Marcar "acesso total"
  dá acesso a tudo, inclusive áreas futuras.
  **Importante**: usuário sem nenhum perfil atribuído continua com o
  comportamento de sempre (staff = acesso total, não-staff = só
  PDV+Caixa) — atribuir um perfil é opcional, só restringe quem você
  quiser restringir.
- **Sessões ativas** (menu lateral, embaixo): mostra quem está
  logado agora, de qual IP, em qual dispositivo/navegador, e desde
  quando. Dá pra **encerrar remotamente** a sessão de qualquer
  usuário — ele é deslogado de verdade na próxima ação que tentar
  fazer.
- **Log de auditoria**: agora também guarda o IP e o
  dispositivo/navegador de cada ação registrada (venda fechada,
  caixa aberto/fechado, devolução, recebimento de ordem de compra),
  não só quem fez e quando.
- Pra recriar os perfis padrão (ex: numa instalação nova), rode
  `python manage.py criar_perfis_padrao`.

## Consulta de carta (menu Cadastros → "Consulta de carta")

Busca rápida — independente de ter o produto cadastrado ou não — em
Magic, Pokémon ou Yu-Gi-Oh!: mostra imagem, edição, raridade, tipo
e um **preço de referência** de mercado (TCGplayer/Cardmarket,
conforme a fonte). Útil pra avaliar uma carta que alguém trouxe pra
vender, sem precisar cadastrar nada antes. O preço é referência do
mercado americano em dólar — sirva como ponto de partida, não como o
preço final que você deve cobrar (câmbio e mercado local variam).

## Busca automática de imagem (Pokémon, Magic, Yu-Gi-Oh)

- **Como configurar**: em Cadastros → Categorias, defina qual "jogo"
  cada categoria representa (Pokémon / Magic / Yu-Gi-Oh). Categorias
  sem jogo definido (acessórios, boxes, etc) não ganham esse recurso
  — pra elas, o upload continua manual.
- **Como usar**: na ficha do produto no admin, aparece um link
  "🔍 Buscar imagem automaticamente". Ele busca até 3 opções nos
  bancos de dados oficiais/comunitários de cada jogo (Scryfall pra
  Magic, pokemontcg.io pra Pokémon, YGOPRODeck pra Yu-Gi-Oh) — você
  escolhe qual bate certo com a carta antes de salvar, evitando pegar
  a imagem errada quando existem várias edições/versões parecidas.
- Essas são fontes gratuitas feitas especificamente pra esse tipo de
  uso — bem diferente de fazer scraping genérico de imagem na
  internet, que teria risco de direito autoral e resultado incerto.

- **Produtos lacrados (booster box, blister, ETB, case)**: mesma
  tela, mas busca pelo **código de barras** (UPC/EAN) via UPCitemdb —
  gratuito, sem precisar de cadastro/chave (100 consultas grátis por
  dia). Não existe um "banco de dados de cartas" pra embalagem, mas
  o código de barras é exato, então costuma ser mais confiável que
  buscar por nome. Preencha o campo EAN ou código de barras na ficha
  do produto e o sistema já usa ele automaticamente na busca. Pra
  produtos do tipo Kit/Combo/Bundle/Caixa/Booster Box/Blister/
  ETB/Case, essa aba já vem selecionada por padrão.

## Fornecedores

- **Avaliação de fornecedor**: nota manual de 1 a 5 estrelas no
  cadastro, lado a lado com os indicadores automáticos (prazo médio
  de entrega, atraso médio, preço médio, valor total comprado) na
  tela de Análise de compras.

## CRM (menu "CRM")

- **Funil de vendas**: quadro com leads organizados por etapa (Novo →
  Em contato → Negociação → Ganho/Perdido). Ao mover um lead pra
  "Ganho", o sistema **cria o cadastro de Cliente automaticamente**.
- **Tarefas**: lembretes simples, manuais ou gerados pelas
  automações, com botão de concluir.
- **Agenda**: suas tarefas pendentes agrupadas por dia.
- **Propostas**: propostas comerciais vinculadas a lead ou cliente,
  com status (aberta/aceita/recusada) e validade.
- **Automações** (ativa em Admin → CRM → Configuração do CRM, e roda
  via `python manage.py rodar_automacoes_crm` — agende isso pra
  rodar 1x por dia, ex: cron ou tarefa agendada do Windows):
  - **Pós-venda**: manda WhatsApp/e-mail automático N dias depois de
    uma venda, perguntando como foi a experiência.
  - **Aniversário**: manda mensagem de parabéns no dia certo.
  - **Lead parado**: cria uma tarefa de follow-up sozinho quando um
    lead fica X dias sem nenhuma interação registrada.
  - Tudo isso reaproveita a mesma configuração de WhatsApp (Twilio)
    e e-mail que já existe pros alertas internos — sem custo ou
    integração nova pra configurar.

## Estrutura do projeto

```
belletti_pdv/
├── core/            # configurações do Django (settings, urls)
├── catalogo/         # produtos e estoque
├── vendas/           # clientes, vendas, itens de venda, PDV
├── financeiro/       # contas a pagar/receber, caixa, categorias
├── requirements.txt
├── Procfile           # comando de deploy do Railway
└── .env.example        # modelo das variáveis de ambiente
```
