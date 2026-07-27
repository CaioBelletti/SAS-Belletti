from django.urls import path

from . import views

app_name = "cozinha"

urlpatterns = [
    path("painel/", views.painel_cozinha, name="painel"),
    path("painel/<int:pedido_id>/avancar/", views.avancar_pedido, name="avancar"),
    path("painel/<int:pedido_id>/prioridade/", views.mudar_prioridade, name="prioridade"),
    path("painel/<int:pedido_id>/cancelar/", views.cancelar_pedido, name="cancelar"),
    path("qrcode/", views.qrcode_cardapio, name="qrcode"),
]
