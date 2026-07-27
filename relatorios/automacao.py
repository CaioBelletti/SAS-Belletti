from django.utils import timezone

from notificacoes.services import enviar_email_para

from .models import get_config_relatorio_automatico
from .views import montar_contexto_dashboard


def deve_enviar_hoje(config):
    hoje = timezone.localdate()
    if config.frequencia == "diario":
        return True
    if config.frequencia == "semanal":
        return hoje.weekday() == 0  # segunda-feira
    if config.frequencia == "anual":
        return hoje.month == 1 and hoje.day == 1
    return hoje.day == 1  # mensal, todo dia 1º do mês


def montar_texto_resumo(ctx):
    linhas = [
        "Resumo Belletti Cards Universe",
        "",
        f"Total de vendas (12 meses): R$ {ctx['total_valor']:.2f}",
        f"Ticket médio: R$ {ctx['ticket_medio']:.2f}",
        f"Pedidos fechados: {ctx['total_pedidos']}",
        f"Itens vendidos: {ctx['produtos_vendidos']}",
        f"Saldo atual em caixa: R$ {ctx['saldo_atual']:.2f}",
        f"A receber (pendente): R$ {ctx['total_a_receber']:.2f}",
        "",
        f"DRE do mês — Lucro líquido: R$ {ctx['dre']['lucro_liquido']:.2f}",
    ]
    if ctx.get("alertas"):
        linhas.append("")
        linhas.append(f"Alertas ativos agora ({len(ctx['alertas'])}):")
        for a in ctx["alertas"][:5]:
            linhas.append(f"  - [{a['nivel']}] {a['titulo']}")
    return "\n".join(linhas)


def enviar_relatorio_automatico(forcar=False):
    config = get_config_relatorio_automatico()
    if not config.ativo or not config.destinatario:
        return False
    if not forcar and not deve_enviar_hoje(config):
        return False
    if not forcar and config.ultimo_envio == timezone.localdate():
        return False  # já enviou hoje, não manda de novo

    ctx = montar_contexto_dashboard()
    texto = montar_texto_resumo(ctx)
    enviar_email_para(config.destinatario, "Resumo periódico — Belletti Cards Universe", texto)

    config.ultimo_envio = timezone.localdate()
    config.save(update_fields=["ultimo_envio"])
    return True
