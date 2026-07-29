from django.urls import path

from . import views

app_name = "crm"

urlpatterns = [
    path("funil/", views.funil, name="funil"),
    path("tarefas/", views.tarefas, name="tarefas"),
    path("agenda/", views.agenda, name="agenda"),
    path("agenda/calendario/", views.agenda_calendario, name="agenda_calendario"),
    path("propostas/", views.propostas, name="propostas"),
]
