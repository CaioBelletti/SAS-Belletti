"""
Comando pra rodar um resumo diário de alertas: contas vencendo,
estoque baixo, e status da meta do mês. Pensado pra ser agendado
(Agendador de Tarefas do Windows, ou cron no Railway) uma vez por dia.

Uso: python manage.py verificar_alertas
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Verifica contas vencendo, estoque baixo e meta do mês, e manda um resumo por e-mail/WhatsApp."

    def handle(self, *args, **options):
        from catalogo.models import Produto
        from financeiro.models import ContaPagar, ContaReceber
        from notificacoes.models import get_config
        from notificacoes.services import notificar
        from relatorios.models import MetaMensal
        from vendas.models import Venda
        from django.db.models import F, Sum

        config = get_config()
        hoje = timezone.localdate()
        limite = hoje + timedelta(days=config.dias_aviso_vencimento)

        partes = []

        contas_pagar = ContaPagar.objects.filter(status="pendente", vencimento__lte=limite).order_by("vencimento")
        contas_receber = ContaReceber.objects.filter(status="pendente", vencimento__lte=limite).order_by("vencimento")
        if contas_pagar.exists() or contas_receber.exists():
            linhas = ["Contas vencendo em breve:"]
            for c in contas_pagar:
                linhas.append(f"  - PAGAR: {c.descricao} — R$ {c.valor} (vence {c.vencimento:%d/%m})")
            for c in contas_receber:
                linhas.append(f"  - RECEBER: {c.descricao} — R$ {c.valor} (vence {c.vencimento:%d/%m})")
            partes.append("\n".join(linhas))

        produtos_baixo = Produto.objects.filter(ativo=True, estoque_atual__lte=F("estoque_minimo"))
        if produtos_baixo.exists():
            linhas = ["Produtos com estoque baixo:"]
            for p in produtos_baixo:
                linhas.append(f"  - {p.nome} ({p.sku}): {p.estoque_atual} unidade(s)")
            partes.append("\n".join(linhas))

        inicio_mes = hoje.replace(day=1)
        meta = MetaMensal.objects.filter(mes=inicio_mes).first()
        if meta and meta.valor > 0:
            vendido = Venda.objects.filter(
                status="fechada", fechada_em__date__gte=inicio_mes
            ).aggregate(total=Sum(F("itens__quantidade") * F("itens__preco_unitario")))["total"] or 0
            percentual = (vendido / meta.valor) * 100
            partes.append(f"Meta do mês: R$ {vendido:.2f} de R$ {meta.valor} ({percentual:.0f}%).")

        if not partes:
            self.stdout.write("Nada pra alertar hoje.")
            return

        mensagem = "\n\n".join(partes)
        notificar("Resumo diário", mensagem)
        self.stdout.write(self.style.SUCCESS("Resumo enviado."))
        self.stdout.write(mensagem)
