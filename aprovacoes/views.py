from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .models import SolicitacaoAprovacao
from .services import (
    AprovacaoJaDecididaError,
    SemPermissaoParaAprovarError,
    decidir,
    usuario_pode_aprovar,
)


@login_required
def aprovacoes_pendentes(request):
    if request.method == "POST":
        solicitacao = get_object_or_404(SolicitacaoAprovacao, pk=request.POST.get("solicitacao_id"))
        decisao = request.POST.get("decisao")
        comentario = request.POST.get("comentario", "").strip()

        try:
            decidir(solicitacao, request.user, decisao, comentario)
            messages.success(request, f"Solicitação #{solicitacao.pk} — {decisao} com sucesso.")
        except AprovacaoJaDecididaError as exc:
            messages.error(request, str(exc))
        except SemPermissaoParaAprovarError as exc:
            messages.error(request, str(exc))

        return redirect("aprovacoes:pendentes")

    todas_pendentes = SolicitacaoAprovacao.objects.filter(status="pendente").select_related(
        "solicitado_por", "content_type"
    )
    minhas_pendentes = [s for s in todas_pendentes if usuario_pode_aprovar(request.user, s)]

    historico = SolicitacaoAprovacao.objects.exclude(status="pendente").select_related(
        "solicitado_por"
    ).prefetch_related("registros")[:20]

    return render(request, "aprovacoes/pendentes.html", {
        "minhas_pendentes": minhas_pendentes,
        "total_pendentes_sistema": todas_pendentes.count(),
        "historico": historico,
    })
