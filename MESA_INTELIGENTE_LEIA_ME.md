# Belletti Mesa Inteligente 1.0

## Recursos
- Identificação persistente do jogador/cliente por dispositivo e mesa.
- Consumo individual e total da mesa.
- Pedidos vinculados ao jogador.
- Favoritos automáticos após 3 unidades/pedidos do mesmo prato.
- Promoções configuráveis no Django Admin, com combos e preço promocional.
- Avaliação de comida e atendimento de 1 a 5.

## Administração
Após o deploy, acesse o Django Admin e configure:
- Cozinha > Promoções do cardápio
- Cozinha > Jogadores/clientes da mesa
- Cozinha > Avaliações das mesas

## Migration
A migration `cozinha.0005_mesa_inteligente_promocoes_avaliacoes` será aplicada pelo Railway.
