from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from vendas.models import Cliente

from .models import CategoriaTarefa, InteracaoContato, Lead, Proposta, Tarefa


@login_required
def funil(request):
    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar_lead":
            Lead.objects.create(
                nome=request.POST.get("nome", "").strip(),
                telefone=request.POST.get("telefone", "").strip(),
                email=request.POST.get("email", "").strip(),
                origem=request.POST.get("origem", "outro"),
                valor_estimado=request.POST.get("valor_estimado") or 0,
                responsavel=request.user,
            )
            messages.success(request, "Lead criado.")
            return redirect("crm:funil")

        lead = get_object_or_404(Lead, pk=request.POST.get("lead_id"))

        if acao == "mover_etapa":
            nova_etapa = request.POST.get("etapa")
            if nova_etapa in dict(Lead.ETAPA_CHOICES):
                lead.etapa = nova_etapa
                lead.save(update_fields=["etapa", "atualizado_em"])
                if nova_etapa == "ganho" and not lead.cliente:
                    cliente = Cliente.objects.create(nome=lead.nome, telefone=lead.telefone, email=lead.email)
                    lead.cliente = cliente
                    lead.save(update_fields=["cliente"])
                    messages.success(request, f"Lead ganho! Cliente '{cliente.nome}' criado automaticamente.")
                else:
                    messages.success(request, f"Lead movido para '{lead.get_etapa_display()}'.")
            return redirect("crm:funil")

        if acao == "registrar_interacao":
            InteracaoContato.objects.create(
                lead=lead, tipo=request.POST.get("tipo", "outro"),
                descricao=request.POST.get("descricao", ""), criada_por=request.user,
            )
            messages.success(request, "Interação registrada.")
            return redirect("crm:funil")

    leads = Lead.objects.select_related("responsavel").order_by("-atualizado_em")
    colunas = {etapa: [] for etapa, _ in Lead.ETAPA_CHOICES}
    for lead in leads:
        colunas[lead.etapa].append(lead)

    return render(request, "crm/funil.html", {
        "colunas": colunas,
        "etapas": Lead.ETAPA_CHOICES,
        "origens": Lead.ORIGEM_CHOICES,
    })


@login_required
def tarefas(request):
    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar":
            from datetime import datetime
            data_str = request.POST.get("data_vencimento")
            data_vencimento = timezone.make_aware(datetime.fromisoformat(data_str)) if data_str else timezone.now()
            Tarefa.objects.create(
                titulo=request.POST.get("titulo", "").strip(),
                descricao=request.POST.get("descricao", "").strip(),
                responsavel=request.user,
                data_vencimento=data_vencimento,
            )
            messages.success(request, "Tarefa criada.")
            return redirect("crm:tarefas")

        if acao == "concluir":
            tarefa = get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id"))
            tarefa.concluida = True
            tarefa.concluida_em = timezone.now()
            tarefa.save(update_fields=["concluida", "concluida_em"])
            return redirect("crm:tarefas")

    pendentes = Tarefa.objects.filter(concluida=False).select_related("lead", "cliente", "responsavel")
    concluidas = Tarefa.objects.filter(concluida=True).select_related("lead", "cliente")[:15]

    return render(request, "crm/tarefas.html", {
        "pendentes": pendentes,
        "concluidas": concluidas,
    })


@login_required
def agenda_calendario(request):
    import calendar as calendar_mod
    from datetime import date, datetime

    hoje = timezone.localdate()
    ano = int(request.GET.get("ano", hoje.year))
    mes = int(request.GET.get("mes", hoje.month))

    if request.method == "POST":
        acao = request.POST.get("acao")
        if acao == "criar":
            data_str = request.POST.get("data_vencimento")
            data_vencimento = timezone.make_aware(datetime.fromisoformat(data_str)) if data_str else timezone.now()
            Tarefa.objects.create(
                titulo=request.POST.get("titulo", "").strip(),
                descricao=request.POST.get("descricao", "").strip(),
                categoria_id=request.POST.get("categoria_id") or None,
                responsavel=request.user,
                data_vencimento=data_vencimento,
            )
            messages.success(request, "Tarefa adicionada à agenda.")
        elif acao == "concluir":
            tarefa = get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id"))
            tarefa.concluida = True
            tarefa.concluida_em = timezone.now()
            tarefa.save(update_fields=["concluida", "concluida_em"])
        return redirect(f"{reverse('crm:agenda_calendario')}?ano={ano}&mes={mes}")

    cal = calendar_mod.Calendar(firstweekday=6)  # semana começa no domingo
    dias_do_mes = list(cal.itermonthdates(ano, mes))

    tarefas_qs = (
        Tarefa.objects.filter(data_vencimento__year=ano, data_vencimento__month=mes)
        .select_related("categoria")
        .order_by("data_vencimento")
    )
    tarefas_por_dia = {}
    for t in tarefas_qs:
        tarefas_por_dia.setdefault(t.data_vencimento.date(), []).append(t)

    celulas = [
        {
            "data": dia, "numero": dia.day, "no_mes": dia.month == mes, "hoje": dia == hoje,
            "tarefas": tarefas_por_dia.get(dia, []),
        }
        for dia in dias_do_mes
    ]
    semanas = [celulas[i:i + 7] for i in range(0, len(celulas), 7)]

    mes_anterior = mes - 1 if mes > 1 else 12
    ano_mes_anterior = ano if mes > 1 else ano - 1
    proximo_mes = mes + 1 if mes < 12 else 1
    ano_proximo_mes = ano if mes < 12 else ano + 1

    return render(request, "crm/agenda_calendario.html", {
        "semanas": semanas,
        "mes_atual": date(ano, mes, 1),
        "hoje": hoje,
        "categorias": CategoriaTarefa.objects.all(),
        "ano": ano, "mes": mes,
        "mes_anterior": mes_anterior, "ano_mes_anterior": ano_mes_anterior,
        "proximo_mes": proximo_mes, "ano_proximo_mes": ano_proximo_mes,
    })


@login_required
def agenda(request):
    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar":
            from datetime import datetime
            data_str = request.POST.get("data_vencimento")
            data_vencimento = timezone.make_aware(datetime.fromisoformat(data_str)) if data_str else timezone.now()
            Tarefa.objects.create(
                titulo=request.POST.get("titulo", "").strip(),
                descricao=request.POST.get("descricao", "").strip(),
                responsavel=request.user,
                data_vencimento=data_vencimento,
            )
            messages.success(request, "Tarefa adicionada à agenda.")

        elif acao == "concluir":
            tarefa = get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id"))
            tarefa.concluida = True
            tarefa.concluida_em = timezone.now()
            tarefa.save(update_fields=["concluida", "concluida_em"])

        return redirect("crm:agenda")

    tarefas_qs = (
        Tarefa.objects.filter(concluida=False)
        .select_related("lead", "cliente")
        .order_by("data_vencimento")
    )
    agrupado = {}
    for t in tarefas_qs:
        chave = t.data_vencimento.date()
        agrupado.setdefault(chave, []).append(t)

    dias = sorted(agrupado.keys())
    return render(request, "crm/agenda.html", {
        "dias": [{"data": d, "tarefas": agrupado[d]} for d in dias],
        "hoje": timezone.localdate(),
    })


@login_required
def propostas(request):
    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao == "criar":
            Proposta.objects.create(
                titulo=request.POST.get("titulo", "").strip(),
                descricao=request.POST.get("descricao", "").strip(),
                lead_id=request.POST.get("lead_id") or None,
                cliente_id=request.POST.get("cliente_id") or None,
                valor=request.POST.get("valor") or 0,
                validade=request.POST.get("validade") or None,
            )
            messages.success(request, "Proposta criada.")
            return redirect("crm:propostas")

        if acao in ("aceitar", "recusar"):
            proposta = get_object_or_404(Proposta, pk=request.POST.get("proposta_id"))
            proposta.status = "aceita" if acao == "aceitar" else "recusada"
            proposta.save(update_fields=["status"])
            return redirect("crm:propostas")

    return render(request, "crm/propostas.html", {
        "propostas_abertas": Proposta.objects.filter(status="aberta").select_related("lead", "cliente"),
        "propostas_fechadas": Proposta.objects.exclude(status="aberta").select_related("lead", "cliente")[:15],
        "leads": Lead.objects.exclude(etapa="perdido").order_by("nome"),
        "clientes": Cliente.objects.order_by("nome"),
    })
