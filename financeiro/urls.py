from django.urls import path

from . import views

app_name = "financeiro"

urlpatterns = [
    path("caixa/", views.caixa, name="caixa"),
    path("lancar-parcelado/", views.lancar_parcelado, name="lancar_parcelado"),
    path("bancos/", views.bancos, name="bancos"),
    path("bancos/<int:conta_id>/extrato/", views.extrato_bancario, name="extrato"),
    path("bancos/<int:conta_id>/importar/", views.importar_ofx, name="importar_ofx"),
    path("bancos/<int:conta_id>/conciliar/", views.conciliar, name="conciliar"),
]
