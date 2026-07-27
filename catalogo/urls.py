from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("etiquetas/", views.etiquetas, name="etiquetas"),
    path("composicao/", views.composicao, name="composicao"),
    path("inventario/", views.inventario, name="inventario"),
    path("perdas/", views.perdas, name="perdas"),
    path("reservas/", views.reservas, name="reservas"),
    path("produto/<int:produto_id>/buscar-imagem/", views.buscar_imagem_produto, name="buscar_imagem_produto"),
    path("consulta-carta/", views.consulta_carta, name="consulta_carta"),
]
