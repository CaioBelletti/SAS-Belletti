from django.urls import path

from . import bi_views, central_views, inteligencia_views, views

app_name = "relatorios"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("exportar/", views.exportar_excel, name="exportar_excel"),
    path("salvar-preferencia/", views.salvar_preferencia_dashboard, name="salvar_preferencia"),
    path("central/", central_views.central_relatorios, name="central"),
    path("inteligencia/", inteligencia_views.inteligencia_view, name="inteligencia"),
    path("bi/", bi_views.bi_avancado, name="bi_avancado"),
    path("bi/exportar-csv/", bi_views.bi_exportar_csv, name="bi_exportar_csv"),
    path("bi/exportar-pdf/", bi_views.bi_exportar_pdf, name="bi_exportar_pdf"),
]
