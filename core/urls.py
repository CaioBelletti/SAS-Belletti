from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve

from core.backup_views import baixar_backup
from core.pwa_views import sw_view
from cozinha import views as cozinha_views
from seguranca import views as seguranca_views

admin.site.site_header = "Belletti Cards Universe"
admin.site.site_title = "Belletti Cards Universe"
admin.site.index_title = "Painel administrativo"

from core import registration_views, operations_views

urlpatterns = [
    path("crm/automacoes/", operations_views.screen, {"kind":"automacoes"}, name="workspace_automacoes"),
    path("financeiro/contas-a-pagar/", operations_views.screen, {"kind":"pagar"}, name="workspace_pagar"),
    path("financeiro/contas-a-receber/", operations_views.screen, {"kind":"receber"}, name="workspace_receber"),
    path("financeiro/metas/", operations_views.screen, {"kind":"metas"}, name="workspace_metas"),
    path("cadastros/fornecedores/<int:pk>/excluir/", registration_views.supplier_delete, name="supplier_delete"),
    path("cadastros/<slug:kind>/", registration_views.registration_list, name="registration_list"),
    path("cadastros/<slug:kind>/novo/", registration_views.registration_form, name="registration_new"),
    path("cadastros/<slug:kind>/<int:pk>/", registration_views.registration_form, name="registration_edit"),
    path("admin/login/", RedirectView.as_view(pattern_name="login", query_string=True)),
    path("admin/", admin.site.urls),
    path("login/", seguranca_views.login_view, name="login"),
    path(
        "logout/",
        auth_views.LogoutView.as_view(next_page="login"),
        name="logout",
    ),
    path("seguranca/", include("seguranca.urls")),
    path("backup/", baixar_backup, name="backup"),
    path("relatorios/", include("relatorios.urls")),
    path("pdv/", include("vendas.urls")),
    path("suprimentos/", include("suprimentos.urls")),
    path("financeiro/", include("financeiro.urls")),
    path("catalogo/", include("catalogo.urls")),
    path("crm/", include("crm.urls")),
    path("notificacoes/", include("notificacoes.urls")),
    path("aprovacoes/", include("aprovacoes.urls")),
    path("cozinha/", include("cozinha.urls")),
    path(
        "cardapio/",
        cozinha_views.cardapio_publico,
        name="cardapio_publico",
    ),
    path(
        "cardapio/pedido/",
        cozinha_views.fazer_pedido,
        name="fazer_pedido",
    ),
    path(
        "cardapio/acompanhar/<str:codigo>/",
        cozinha_views.acompanhar_pedido,
        name="acompanhar_pedido",
    ),
    path(
        "cardapio/m/<uuid:token>/",
        cozinha_views.confirmar_mesa,
        name="confirmar_mesa",
    ),
    path(
        "cardapio/m/<uuid:token>/cardapio/",
        cozinha_views.cardapio_mesa,
        name="cardapio_mesa",
    ),
    path(
        "cardapio/m/<uuid:token>/chamar/",
        cozinha_views.chamar_atendente,
        name="chamar_atendente",
    ),
    path(
        "cardapio/m/<uuid:token>/preferencias/",
        cozinha_views.preferencias_mesa,
        name="preferencias_mesa",
    ),
    path(
        "cardapio/m/<uuid:token>/avaliar/",
        cozinha_views.avaliar_experiencia,
        name="avaliar_experiencia",
    ),
    path("sw.js", sw_view, name="sw"),
    path(
        "",
        RedirectView.as_view(
            url="relatorios/",
            permanent=False,
        ),
    ),
    re_path(
        r"^media/(?!backups_privados/)(?P<path>.*)$",
        serve,
        {"document_root": settings.MEDIA_ROOT},
    ),
]