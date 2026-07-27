from django.urls import path

from . import views

app_name = "vendas"

urlpatterns = [
    path("", views.pdv, name="pdv"),
    path("api/produtos/", views.api_buscar_produtos, name="api_buscar_produtos"),
    path("api/validar-cupom/", views.api_validar_cupom, name="api_validar_cupom"),
    path("api/validar-vale/", views.api_validar_vale, name="api_validar_vale"),
    path("api/finalizar/", views.api_finalizar_venda, name="api_finalizar_venda"),
    path("api/orcamento/", views.api_salvar_orcamento, name="api_salvar_orcamento"),
    path("api/produtos-offline/", views.api_produtos_offline, name="api_produtos_offline"),
    path("api/sincronizar-offline/", views.api_sincronizar_offline, name="api_sincronizar_offline"),
]
