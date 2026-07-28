from django.urls import path

from . import views

app_name = "cozinha"

urlpatterns = [
    path("painel/", views.painel_cozinha, name="painel"),
    path("painel/<int:pedido_id>/avancar/", views.avancar_pedido, name="avancar"),
    path("painel/checklist/<int:checklist_id>/alternar/", views.alternar_checklist, name="alternar_checklist"),
    path("painel/dados/", views.dados_painel, name="dados_painel"),
    path("painel/<int:pedido_id>/prioridade/", views.mudar_prioridade, name="prioridade"),
    path("painel/<int:pedido_id>/cancelar/", views.cancelar_pedido, name="cancelar"),
    path("painel/chamado/<int:chamado_id>/atender/", views.atender_chamado, name="atender_chamado"),
    path("mesas-abertas/", views.mesas_abertas, name="mesas_abertas"),
    path("qrcode/", views.qrcode_cardapio, name="qrcode"),
    path("qrcode/mesa/<int:mesa_id>/", views.qrcode_mesa, name="qrcode_mesa"),
    path("qrcode/todas-mesas/", views.qrcodes_todas_mesas_pdf, name="qrcodes_todas_mesas"),
]
