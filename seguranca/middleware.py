from django.contrib import messages
from django.shortcuts import redirect
from django.utils import timezone

MAPA_AREAS = {
    "/pdv/": "pdv",
    "/financeiro/": "financeiro",
    "/catalogo/": "catalogo",
    "/suprimentos/": "suprimentos",
    "/relatorios/": "relatorios",
    "/crm/": "crm",
    "/cozinha/": "cozinha",
    "/admin/": "admin_completo",
}

# Caminhos que nunca são bloqueados, mesmo sem permissão de área
# (login, logout, 2FA, backup, arquivos estáticos/mídia).
CAMINHOS_LIVRES = ("/login/", "/logout/", "/seguranca/", "/backup/", "/static/", "/media/")

# Perfil padrão pra quem nunca recebeu um Grupo (perfil) — mantém o
# comportamento de antes do sistema de perfis existir.
AREAS_PADRAO_STAFF = {"*"}
AREAS_PADRAO_VENDEDOR = {"pdv", "financeiro"}  # financeiro aqui só cobre a tela de Caixa, ver view


def _area_da_url(path):
    for prefixo, area in MAPA_AREAS.items():
        if path.startswith(prefixo):
            return area
    return None


def _areas_permitidas(user):
    """Devolve o conjunto de áreas que esse usuário pode acessar. {'*'} = tudo."""
    from .models import PerfilAcesso

    perfis = PerfilAcesso.objects.filter(grupo__in=user.groups.all()).prefetch_related("areas")
    if not perfis.exists():
        # nunca recebeu um perfil — usa o comportamento padrão de sempre
        return AREAS_PADRAO_STAFF if user.is_staff else AREAS_PADRAO_VENDEDOR

    areas = set()
    for perfil in perfis:
        if perfil.acesso_total:
            return {"*"}
        areas.update(a.codigo for a in perfil.areas.all())
    return areas


class ControleDeAreaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated or request.user.is_superuser:
            return self.get_response(request)

        if request.path.startswith(CAMINHOS_LIVRES):
            return self.get_response(request)

        area = _area_da_url(request.path)
        if area is None:
            return self.get_response(request)

        permitidas = _areas_permitidas(request.user)
        if "*" in permitidas or area in permitidas:
            return self.get_response(request)

        messages.error(request, "Seu perfil não tem acesso a essa área do sistema.")
        return redirect("/")


class AtualizarSessaoAtivaMiddleware:
    """Atualiza 'última atividade' da sessão a cada request autenticado."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.user.is_authenticated and request.session.session_key:
            from .models import SessaoAtiva
            SessaoAtiva.objects.filter(session_key=request.session.session_key).update(
                ultima_atividade=timezone.now()
            )
        return response


class RateLimitEIPBloqueadoMiddleware:
    """
    Duas proteções básicas de borda:
    1. Bloqueia de vez qualquer IP cadastrado em IPBloqueado.
    2. Rate limit geral — mais de LIMITE_REQUISICOES requisições do
       mesmo IP em JANELA_SEGUNDOS leva a um 429 (não é rígido pra
       uso normal do sistema, só freia abuso/varredura automatizada).
    """
    LIMITE_REQUISICOES = 180
    JANELA_SEGUNDOS = 60

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.core.cache import cache
        from django.http import HttpResponse

        from .models import IPBloqueado
        from .services import get_ip

        ip = get_ip(request)

        if ip and IPBloqueado.objects.filter(ip=ip).exists():
            return HttpResponse("Acesso bloqueado.", status=403)

        if ip:
            chave = f"ratelimit:{ip}"
            contagem = cache.get(chave, 0)
            if contagem >= self.LIMITE_REQUISICOES:
                return HttpResponse("Muitas requisições — tente de novo em instantes.", status=429)
            cache.set(chave, contagem + 1, self.JANELA_SEGUNDOS)

        return self.get_response(request)
