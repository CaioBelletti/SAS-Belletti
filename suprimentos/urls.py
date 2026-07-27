from django.urls import path

from . import views

app_name = "suprimentos"

urlpatterns = [
    path("importar/", views.importar_upload, name="importar_upload"),
    path("importar/confirmar/", views.importar_confirmar, name="importar_confirmar"),
    path("conferencia/", views.conferencia_recebimento, name="conferencia"),
    path("cotacoes/", views.cotacoes, name="cotacoes"),
    path("analise/", views.analise_compras, name="analise"),
]
