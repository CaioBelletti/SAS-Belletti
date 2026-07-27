from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from crm.models import Lead, Tarefa, get_config_crm
from notificacoes.services import enviar_email_para, enviar_whatsapp_para
from vendas.models import Cliente, Venda


class Command(BaseCommand):
    help = (
        "Roda as automações diárias do sistema: pós-venda, aniversário, follow-up "
        "de lead parado, cobrança de conta vencida, reposição automática de "
        "estoque, e envio do relatório periódico. Agende pra rodar 1x por dia."
    )

    def handle(self, *args, **options):
        config = get_config_crm()
        hoje = timezone.localdate()

        # --- Pós-venda -----------------------------------------------------------
        if config.posvenda_ativo:
            data_alvo = hoje - timedelta(days=config.posvenda_dias)
            vendas = Venda.objects.filter(
                status="fechada", fechada_em__date=data_alvo,
                mensagem_posvenda_enviada=False, cliente__isnull=False,
            ).select_related("cliente")
            enviadas = 0
            for venda in vendas:
                cliente = venda.cliente
                if cliente.anonimizado:
                    continue
                mensagem = config.posvenda_mensagem.format(nome=cliente.nome)
                if cliente.telefone:
                    enviar_whatsapp_para(cliente.telefone, mensagem)
                if cliente.email:
                    enviar_email_para(cliente.email, "Como foi sua experiência?", mensagem)
                venda.mensagem_posvenda_enviada = True
                venda.save(update_fields=["mensagem_posvenda_enviada"])
                enviadas += 1
            self.stdout.write(f"Pós-venda: {enviadas} mensagem(ns) enviada(s).")

        # --- Aniversário -----------------------------------------------------------
        if config.aniversario_ativo:
            aniversariantes = Cliente.objects.filter(
                data_nascimento__month=hoje.month, data_nascimento__day=hoje.day, anonimizado=False,
            )
            enviadas = 0
            for cliente in aniversariantes:
                ja_enviado_hoje = cliente.interacoes.filter(
                    tipo="whatsapp", descricao__startswith="[Automação aniversário]", criada_em__date=hoje,
                ).exists()
                if ja_enviado_hoje:
                    continue
                mensagem = config.aniversario_mensagem.format(nome=cliente.nome)
                if cliente.telefone:
                    enviar_whatsapp_para(cliente.telefone, mensagem)
                if cliente.email:
                    enviar_email_para(cliente.email, "Feliz aniversário! 🎉", mensagem)
                from crm.models import InteracaoContato
                InteracaoContato.objects.create(
                    cliente=cliente, tipo="whatsapp",
                    descricao=f"[Automação aniversário] Mensagem enviada em {hoje}.",
                )
                enviadas += 1
            self.stdout.write(f"Aniversário: {enviadas} mensagem(ns) enviada(s).")

        # --- Lead parado -----------------------------------------------------------
        if config.lead_parado_ativo:
            leads_ativos = Lead.objects.exclude(etapa__in=["ganho", "perdido"])
            responsavel_padrao = get_user_model().objects.filter(is_staff=True).first()
            criadas = 0
            for lead in leads_ativos:
                if lead.dias_sem_interacao < config.lead_parado_dias:
                    continue
                ja_tem_tarefa_aberta = lead.tarefas.filter(concluida=False, gerada_automaticamente=True).exists()
                if ja_tem_tarefa_aberta:
                    continue
                Tarefa.objects.create(
                    titulo=f"Follow-up: {lead.nome} está parado há {lead.dias_sem_interacao} dias",
                    descricao="Gerado automaticamente pelo CRM — sem interação registrada recentemente.",
                    responsavel=lead.responsavel or responsavel_padrao,
                    lead=lead,
                    data_vencimento=timezone.now(),
                    gerada_automaticamente=True,
                )
                criadas += 1
            self.stdout.write(f"Lead parado: {criadas} tarefa(s) criada(s).")

        # --- Recuperação de carrinho abandonado -----------------------------------
        if config.recuperacao_carrinho_ativa:
            limite = timezone.now() - timedelta(hours=config.recuperacao_carrinho_horas)
            pedidos_abertos = Venda.objects.filter(
                status="aberta", aberta_em__lte=limite, mensagem_recuperacao_enviada=False,
                cliente__isnull=False,
            ).select_related("cliente")
            enviadas = 0
            for pedido in pedidos_abertos:
                cliente = pedido.cliente
                if cliente.anonimizado:
                    continue
                mensagem = config.recuperacao_carrinho_mensagem.format(nome=cliente.nome)
                if cliente.telefone:
                    enviar_whatsapp_para(cliente.telefone, mensagem)
                if cliente.email:
                    enviar_email_para(cliente.email, "Sua compra ficou pela metade!", mensagem)
                pedido.mensagem_recuperacao_enviada = True
                pedido.save(update_fields=["mensagem_recuperacao_enviada"])
                enviadas += 1
            self.stdout.write(f"Recuperação de carrinho: {enviadas} mensagem(ns) enviada(s).")

        # --- Cobrança automática de conta vencida ---------------------------------
        from financeiro.models import ContaReceber, get_config_cobranca

        config_cobranca = get_config_cobranca()
        if config_cobranca.ativo:
            data_limite = hoje - timedelta(days=config_cobranca.dias_apos_vencimento)
            contas_vencidas = ContaReceber.objects.filter(
                status="pendente", vencimento__lte=data_limite, cliente__isnull=False,
            ).select_related("cliente")
            enviadas = 0
            for conta in contas_vencidas:
                cliente = conta.cliente
                if cliente.anonimizado:
                    continue
                if conta.ultima_cobranca_enviada and (hoje - conta.ultima_cobranca_enviada).days < config_cobranca.intervalo_entre_cobrancas_dias:
                    continue
                mensagem = config_cobranca.mensagem.format(
                    nome=cliente.nome, descricao=conta.descricao,
                    valor=f"{conta.valor:.2f}", vencimento=conta.vencimento.strftime("%d/%m/%Y"),
                )
                if cliente.telefone:
                    enviar_whatsapp_para(cliente.telefone, mensagem)
                if cliente.email:
                    enviar_email_para(cliente.email, "Conta pendente", mensagem)
                conta.ultima_cobranca_enviada = hoje
                conta.save(update_fields=["ultima_cobranca_enviada"])
                enviadas += 1
            self.stdout.write(f"Cobrança: {enviadas} mensagem(ns) enviada(s).")

        # --- Reposição automática de estoque --------------------------------------
        from catalogo.services import gerar_reposicao_automatica

        ordens = gerar_reposicao_automatica()
        self.stdout.write(f"Reposição automática: {len(ordens)} ordem(ns) de compra gerada(s).")

        # --- Relatório automático por e-mail ---------------------------------------
        from relatorios.automacao import enviar_relatorio_automatico

        enviado = enviar_relatorio_automatico()
        self.stdout.write(f"Relatório automático: {'enviado' if enviado else 'não era hoje / desativado'}.")

        # --- Push de alertas urgentes -----------------------------------------------
        from notificacoes.services import enviar_push_para_staff
        from relatorios.views import montar_contexto_dashboard

        alertas_urgentes = [
            a for a in montar_contexto_dashboard().get("alertas", []) if a["nivel"] == "urgente"
        ]
        if alertas_urgentes:
            titulo = f"⚠️ {len(alertas_urgentes)} alerta(s) urgente(s)"
            corpo = " · ".join(a["titulo"] for a in alertas_urgentes[:3])
            total_enviados = enviar_push_para_staff(titulo, corpo)
            self.stdout.write(f"Push de alertas urgentes: {total_enviados} notificação(ões) enviada(s).")
        else:
            self.stdout.write("Push de alertas urgentes: nada urgente agora.")
