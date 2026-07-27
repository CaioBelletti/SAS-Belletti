from django.urls import path

from . import views

app_name = "aprovacoes"

urlpatterns = [
    path("pendentes/", views.aprovacoes_pendentes, name="pendentes"),
]
