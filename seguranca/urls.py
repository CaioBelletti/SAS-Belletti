from django.urls import path

from . import views

app_name = "seguranca"

urlpatterns = [
    path("verificar-2fa/", views.verificar_2fa_view, name="verificar_2fa"),
    path("configurar-2fa/", views.configurar_2fa_view, name="configurar_2fa"),
    path("sessoes/", views.sessoes_view, name="sessoes"),
]
