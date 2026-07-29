from calendar import monthrange
from datetime import date, datetime, time, timedelta

from django.db import transaction
from django.utils import timezone

from .models import CategoriaTarefa, Tarefa


CATEGORIAS_PADRAO = {
    "Financeiro — pagar": ("#ff6b6b", "money", 10),
    "Financeiro — receber": ("#3ecf8e", "money", 11),
    "Compras e fornecedores": ("#4d9fff", "truck", 20),
    "Eventos e feiras": ("#8b6cf2", "star", 30),
    "Marketing": ("#ff6b8a", "megaphone", 40),
    "Pessoal": ("#2ec4b6", "user", 50),
    "Manutenção": ("#e76f51", "tools", 60),
    "Aniversários": ("#ffb020", "star", 70),
    "Operação da loja": ("#9b5de5", "briefcase", 80),
}


def garantir_categorias():
    resultado = {}
    for nome, (cor, icone, ordem) in CATEGORIAS_PADRAO.items():
        obj, _ = CategoriaTarefa.objects.get_or_create(
            nome=nome,
            defaults={"cor": cor, "icone": icone, "ordem": ordem, "ativa": True},
        )
        resultado[nome] = obj
    return resultado


def _aware_em(data_obj, hora=time(9, 0)):
    dt = datetime.combine(data_obj, hora)
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _criar_automatico(*, origem, referencia_modelo, referencia_id, defaults):
    tarefa, criada = Tarefa.objects.get_or_create(
        origem=origem,
        referencia_modelo=referencia_modelo,
        referencia_id=referencia_id,
        defaults={**defaults, "gerada_automaticamente": True},
    )
    if not criada and not tarefa.concluida:
        campos = []
        for campo, valor in defaults.items():
            if getattr(tarefa, campo) != valor:
                setattr(tarefa, campo, valor)
                campos.append(campo)
        if campos:
            tarefa.save(update_fields=campos)
    return criada


@transaction.atomic
def sincronizar_agenda(usuario=None, dias=90):
    categorias = garantir_categorias()
    hoje = timezone.localdate()
    limite = hoje + timedelta(days=dias)
    criadas = 0

    try:
        from financeiro.models import ContaPagar, ContaReceber
        for conta in ContaPagar.objects.filter(status="pendente", vencimento__lte=limite):
            criadas += _criar_automatico(
                origem="financeiro_pagar", referencia_modelo="financeiro.ContaPagar", referencia_id=conta.pk,
                defaults={
                    "titulo": f"Pagar: {conta.descricao}",
                    "descricao": f"Fornecedor: {conta.fornecedor or 'não informado'} | Valor: R$ {conta.valor}",
                    "categoria": categorias["Financeiro — pagar"], "responsavel": usuario,
                    "data_vencimento": _aware_em(conta.vencimento), "dia_inteiro": True,
                    "prioridade": "urgente" if conta.vencimento < hoje else "alta",
                    "visibilidade": "gestores", "lembrete_minutos": 1440,
                },
            )
        for conta in ContaReceber.objects.filter(status="pendente", vencimento__lte=limite):
            criadas += _criar_automatico(
                origem="financeiro_receber", referencia_modelo="financeiro.ContaReceber", referencia_id=conta.pk,
                defaults={
                    "titulo": f"Receber: {conta.descricao}",
                    "descricao": f"Valor: R$ {conta.valor}",
                    "categoria": categorias["Financeiro — receber"], "responsavel": usuario,
                    "data_vencimento": _aware_em(conta.vencimento), "dia_inteiro": True,
                    "prioridade": "alta" if conta.vencimento <= hoje else "normal",
                    "visibilidade": "gestores", "lembrete_minutos": 1440,
                },
            )
    except Exception:
        pass

    try:
        from suprimentos.models import OrdemCompra
        ordens = OrdemCompra.objects.exclude(status__in=["recebida", "cancelada"]).filter(data_prevista__isnull=False, data_prevista__lte=limite)
        for ordem in ordens:
            criadas += _criar_automatico(
                origem="compra", referencia_modelo="suprimentos.OrdemCompra", referencia_id=ordem.pk,
                defaults={
                    "titulo": f"Receber OC #{ordem.pk} — {ordem.fornecedor.nome}",
                    "descricao": "Conferir volumes, itens, divergências e dar entrada no estoque.",
                    "categoria": categorias["Compras e fornecedores"], "responsavel": usuario,
                    "data_vencimento": _aware_em(ordem.data_prevista), "dia_inteiro": True,
                    "prioridade": "alta" if ordem.data_prevista <= hoje else "normal",
                    "visibilidade": "equipe", "lembrete_minutos": 1440,
                },
            )
    except Exception:
        pass

    try:
        from vendas.models import Cliente
        for cliente in Cliente.objects.filter(data_nascimento__isnull=False, anonimizado=False):
            nasc = cliente.data_nascimento
            ano = hoje.year
            dia = min(nasc.day, monthrange(ano, nasc.month)[1])
            aniversario = date(ano, nasc.month, dia)
            if aniversario < hoje:
                ano += 1
                dia = min(nasc.day, monthrange(ano, nasc.month)[1])
                aniversario = date(ano, nasc.month, dia)
            if aniversario <= limite:
                referencia = cliente.pk * 10000 + ano
                criadas += _criar_automatico(
                    origem="aniversario", referencia_modelo="vendas.Cliente", referencia_id=referencia,
                    defaults={
                        "titulo": f"Aniversário: {cliente.nome}",
                        "descricao": "Enviar mensagem personalizada e avaliar benefício de fidelidade.",
                        "categoria": categorias["Aniversários"], "responsavel": usuario,
                        "data_vencimento": _aware_em(aniversario), "dia_inteiro": True,
                        "prioridade": "normal", "visibilidade": "gestores", "lembrete_minutos": 1440,
                    },
                )
    except Exception:
        pass
    return criadas


def criar_checklist_operacional(usuario, data_ref=None):
    categorias = garantir_categorias()
    data_ref = data_ref or timezone.localdate()
    itens = [
        ("Abertura da loja", time(9, 0), "Conferir caixa, iluminação, internet, ar-condicionado e limpeza."),
        ("Revisar pedidos e entregas do dia", time(10, 0), "Separar prioridades de fornecedores, clientes e cozinha."),
        ("Fechamento da loja", time(22, 0), "Conferir caixa, estoque crítico, equipamentos, portas e alarmes."),
    ]
    criadas = 0
    for indice, (titulo, hora, descricao) in enumerate(itens, start=1):
        referencia = int(data_ref.strftime("%Y%m%d")) * 10 + indice
        criadas += _criar_automatico(
            origem="checklist", referencia_modelo="operacao.ChecklistDiario", referencia_id=referencia,
            defaults={
                "titulo": titulo, "descricao": descricao,
                "categoria": categorias["Operação da loja"], "responsavel": usuario,
                "data_vencimento": _aware_em(data_ref, hora), "dia_inteiro": False,
                "prioridade": "alta", "visibilidade": "equipe", "lembrete_minutos": 30,
            },
        )
    return criadas


def proxima_data_recorrente(tarefa):
    atual = tarefa.data_vencimento
    if tarefa.recorrencia == "diaria":
        return atual + timedelta(days=1)
    if tarefa.recorrencia == "semanal":
        return atual + timedelta(days=7)
    if tarefa.recorrencia == "mensal":
        ano = atual.year + (1 if atual.month == 12 else 0)
        mes = 1 if atual.month == 12 else atual.month + 1
        dia = min(atual.day, monthrange(ano, mes)[1])
        return atual.replace(year=ano, month=mes, day=dia)
    if tarefa.recorrencia == "anual":
        ano = atual.year + 1
        dia = min(atual.day, monthrange(ano, atual.month)[1])
        return atual.replace(year=ano, day=dia)
    return None
