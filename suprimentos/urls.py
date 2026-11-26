from django.urls import path

from . import views, workspace_views

app_name = "suprimentos"

urlpatterns = [
    path("ordens/", workspace_views.ordens, name="ordens"),
    path("ordens/<int:pk>/", workspace_views.ordem_detalhe, name="ordem_detalhe"),
    path("importar/", views.importar_upload, name="importar_upload"),
    path("importar/confirmar/", views.importar_confirmar, name="importar_confirmar"),
    path("conferencia/", views.conferencia_recebimento, name="conferencia"),
    path("cotacoes/", views.cotacoes, name="cotacoes"),
    path("analise/", views.analise_compras, name="analise"),
]
