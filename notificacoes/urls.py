from django.urls import path

from . import views

app_name = "notificacoes"

urlpatterns = [
    path("push/chave-publica/", views.api_chave_publica_push, name="chave_publica_push"),
    path("push/inscrever/", views.api_inscrever_push, name="inscrever_push"),
    path("push/desinscrever/", views.api_desinscrever_push, name="desinscrever_push"),
]
