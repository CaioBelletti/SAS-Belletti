from decimal import Decimal

from django.test import TestCase

from catalogo.models import Categoria, MovimentacaoEstoque, Produto
from financeiro.models import ContaReceber, MovimentoCaixa

from .models import ItemVenda, Venda
from .services import EstoqueInsuficienteError, fechar_venda


class FluxoVendaCompletoTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome="Pokémon")
        self.produto = Produto.objects.create(
            sku="PKM-001",
            nome="Charizard VMAX",
            categoria=self.categoria,
            preco_custo=Decimal("50.00"),
            preco_venda=Decimal("120.00"),
        )
        MovimentacaoEstoque.objects.create(
            produto=self.produto, tipo="entrada", quantidade=5, motivo="Estoque inicial"
        )
        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)

    def test_fechar_venda_a_vista_baixa_estoque_e_lanca_financeiro(self):
        venda = Venda.objects.create(forma_pagamento="pix")
        ItemVenda.objects.create(
            venda=venda, produto=self.produto, quantidade=2, preco_unitario=Decimal("120.00")
        )

        fechar_venda(venda)

        self.produto.refresh_from_db()
        venda.refresh_from_db()

        self.assertEqual(self.produto.estoque_atual, 3)
        self.assertEqual(venda.status, "fechada")

        conta = ContaReceber.objects.get(venda=venda)
        self.assertEqual(conta.status, "recebido")
        self.assertEqual(conta.valor, Decimal("240.00"))

        self.assertTrue(
            MovimentoCaixa.objects.filter(conta_receber=conta, tipo="entrada").exists()
        )

    def test_fechar_venda_parcelada_nao_baixa_caixa_ainda(self):
        venda = Venda.objects.create(forma_pagamento="credito_parcelado", parcelas=3)
        ItemVenda.objects.create(
            venda=venda, produto=self.produto, quantidade=1, preco_unitario=Decimal("120.00")
        )

        fechar_venda(venda)

        conta = ContaReceber.objects.get(venda=venda)
        self.assertEqual(conta.status, "pendente")
        self.assertFalse(MovimentoCaixa.objects.filter(conta_receber=conta).exists())

    def test_nao_permite_vender_mais_que_o_estoque(self):
        venda = Venda.objects.create(forma_pagamento="dinheiro")
        ItemVenda.objects.create(
            venda=venda, produto=self.produto, quantidade=99, preco_unitario=Decimal("120.00")
        )

        with self.assertRaises(EstoqueInsuficienteError):
            fechar_venda(venda)

        self.produto.refresh_from_db()
        self.assertEqual(self.produto.estoque_atual, 5)  # nada foi descontado
