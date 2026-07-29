from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.db import models
from django.urls import reverse
from django.utils import timezone

from vendas.models import Cliente

from .agenda_services import criar_checklist_operacional, proxima_data_recorrente, sincronizar_agenda
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
    try:
        ano = int(request.GET.get("ano", hoje.year))
        mes = int(request.GET.get("mes", hoje.month))
        if not 1 <= mes <= 12:
            raise ValueError
    except (TypeError, ValueError):
        ano, mes = hoje.year, hoje.month

    def ler_data(valor, padrao=None):
        if not valor:
            return padrao or timezone.now()
        data = datetime.fromisoformat(valor)
        return timezone.make_aware(data) if timezone.is_naive(data) else data

    if request.method == "POST":
        acao = request.POST.get("acao")

        if acao in {"criar", "editar"}:
            titulo = request.POST.get("titulo", "").strip()
            if not titulo:
                messages.error(request, "Informe o título do compromisso.")
            else:
                tarefa = Tarefa() if acao == "criar" else get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id"))
                tarefa.titulo = titulo
                tarefa.descricao = request.POST.get("descricao", "").strip()
                tarefa.categoria_id = request.POST.get("categoria_id") or None
                tarefa.responsavel = tarefa.responsavel or request.user
                tarefa.data_vencimento = ler_data(request.POST.get("data_vencimento"))
                tarefa.data_fim = ler_data(request.POST.get("data_fim"), None) if request.POST.get("data_fim") else None
                tarefa.dia_inteiro = request.POST.get("dia_inteiro") == "on"
                tarefa.prioridade = request.POST.get("prioridade", "normal")
                tarefa.local = request.POST.get("local", "").strip()
                tarefa.recorrencia = request.POST.get("recorrencia", "nenhuma")
                tarefa.lembrete_minutos = request.POST.get("lembrete_minutos") or 30
                tarefa.visibilidade = request.POST.get("visibilidade", "gestores")
                tarefa.save()
                messages.success(request, "Compromisso salvo na agenda.")

        elif acao == "alternar_conclusao":
            tarefa = get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id"))
            tarefa.concluida = not tarefa.concluida
            tarefa.concluida_em = timezone.now() if tarefa.concluida else None
            tarefa.save(update_fields=["concluida", "concluida_em"])
            if tarefa.concluida and tarefa.recorrencia != "nenhuma":
                proxima = proxima_data_recorrente(tarefa)
                if proxima:
                    Tarefa.objects.create(
                        titulo=tarefa.titulo, descricao=tarefa.descricao, categoria=tarefa.categoria,
                        responsavel=tarefa.responsavel, data_vencimento=proxima,
                        data_fim=(tarefa.data_fim + (proxima - tarefa.data_vencimento)) if tarefa.data_fim else None,
                        dia_inteiro=tarefa.dia_inteiro, prioridade=tarefa.prioridade, local=tarefa.local,
                        recorrencia=tarefa.recorrencia, lembrete_minutos=tarefa.lembrete_minutos,
                        visibilidade=tarefa.visibilidade,
                    )
            messages.success(request, "Status do compromisso atualizado.")

        elif acao == "excluir":
            get_object_or_404(Tarefa, pk=request.POST.get("tarefa_id")).delete()
            messages.success(request, "Compromisso excluído.")

        elif acao in {"criar_categoria", "editar_categoria"}:
            nome = request.POST.get("nome_categoria", "").strip()
            cor = request.POST.get("cor_categoria", "#8b6cf2").strip()
            if not nome:
                messages.error(request, "Informe o nome da categoria.")
            else:
                categoria = CategoriaTarefa() if acao == "criar_categoria" else get_object_or_404(
                    CategoriaTarefa, pk=request.POST.get("categoria_id_edicao")
                )
                categoria.nome = nome
                categoria.cor = cor
                categoria.icone = request.POST.get("icone_categoria", "calendar")
                categoria.ordem = request.POST.get("ordem_categoria") or 0
                categoria.ativa = request.POST.get("ativa_categoria") == "on"
                try:
                    categoria.full_clean()
                    categoria.save()
                    messages.success(request, "Categoria salva.")
                except Exception as exc:
                    messages.error(request, f"Não foi possível salvar a categoria: {exc}")

        elif acao == "excluir_categoria":
            categoria = get_object_or_404(CategoriaTarefa, pk=request.POST.get("categoria_id_edicao"))
            categoria.delete()
            messages.success(request, "Categoria excluída. Os compromissos foram mantidos sem categoria.")

        elif acao == "sincronizar_agenda":
            criadas = sincronizar_agenda(request.user)
            messages.success(request, f"Agenda sincronizada. {criadas} novo(s) compromisso(s) incluído(s).")

        elif acao == "criar_checklist":
            criadas = criar_checklist_operacional(request.user)
            messages.success(request, f"Checklist operacional preparado. {criadas} item(ns) novo(s).")

        return redirect(f"{reverse('crm:agenda_calendario')}?ano={ano}&mes={mes}")

    cal = calendar_mod.Calendar(firstweekday=6)
    dias_do_mes = list(cal.itermonthdates(ano, mes))
    inicio_grade, fim_grade = dias_do_mes[0], dias_do_mes[-1]

    categoria_filtro = request.GET.get("categoria")
    tarefas_qs = (
        Tarefa.objects.filter(data_vencimento__date__range=(inicio_grade, fim_grade))
        .filter(models.Q(visibilidade__in=["gestores", "equipe"]) | models.Q(responsavel=request.user))
        .select_related("categoria", "responsavel")
        .order_by("data_vencimento")
    )
    if categoria_filtro:
        tarefas_qs = tarefas_qs.filter(categoria_id=categoria_filtro)

    tarefas_por_dia = {}
    for tarefa in tarefas_qs:
        dia_local = timezone.localtime(tarefa.data_vencimento).date()
        tarefas_por_dia.setdefault(dia_local, []).append(tarefa)

    celulas = [
        {
            "data": dia,
            "data_iso": dia.isoformat(),
            "numero": dia.day,
            "no_mes": dia.month == mes,
            "hoje": dia == hoje,
            "tarefas": tarefas_por_dia.get(dia, []),
        }
        for dia in dias_do_mes
    ]
    semanas = [celulas[i:i + 7] for i in range(0, len(celulas), 7)]

    mes_anterior = mes - 1 if mes > 1 else 12
    ano_mes_anterior = ano if mes > 1 else ano - 1
    proximo_mes = mes + 1 if mes < 12 else 1
    ano_proximo_mes = ano if mes < 12 else ano + 1
    categorias = CategoriaTarefa.objects.all()
    agora = timezone.now()
    fim_semana = agora + timezone.timedelta(days=7)
    tarefas_visiveis = Tarefa.objects.filter(
        models.Q(visibilidade__in=["gestores", "equipe"]) | models.Q(responsavel=request.user)
    )
    tarefas_hoje = tarefas_visiveis.filter(data_vencimento__date=hoje, concluida=False).select_related("categoria").order_by("data_vencimento")
    tarefas_atrasadas = tarefas_visiveis.filter(data_vencimento__lt=agora, concluida=False).count()
    proximos_sete = tarefas_visiveis.filter(data_vencimento__range=(agora, fim_semana), concluida=False).count()
    automaticas_mes = tarefas_visiveis.filter(gerada_automaticamente=True, data_vencimento__year=ano, data_vencimento__month=mes).count()

    return render(request, "crm/agenda_calendario.html", {
        "semanas": semanas,
        "mes_atual": date(ano, mes, 1),
        "hoje": hoje,
        "categorias": categorias,
        "categorias_ativas": categorias.filter(ativa=True),
        "categoria_filtro": categoria_filtro or "",
        "icone_choices": CategoriaTarefa.ICONE_CHOICES,
        "ano": ano,
        "mes": mes,
        "mes_anterior": mes_anterior,
        "ano_mes_anterior": ano_mes_anterior,
        "proximo_mes": proximo_mes,
        "ano_proximo_mes": ano_proximo_mes,
        "tarefas_hoje": tarefas_hoje,
        "tarefas_atrasadas": tarefas_atrasadas,
        "proximos_sete": proximos_sete,
        "automaticas_mes": automaticas_mes,
        "recorrencia_choices": Tarefa.RECORRENCIA_CHOICES,
        "visibilidade_choices": Tarefa.VISIBILIDADE_CHOICES,
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
