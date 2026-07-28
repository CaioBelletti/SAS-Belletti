from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from django.views.generic import RedirectView

from core.backup_views import baixar_backup
from core.pwa_views import sw_view
from cozinha import views as cozinha_views
from seguranca import views as seguranca_views

admin.site.site_header = "Belletti Cards Universe"
admin.site.site_title = "Belletti Cards Universe"
admin.site.index_title = "Painel administrativo"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', seguranca_views.login_view, name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('seguranca/', include('seguranca.urls')),
    path('backup/', baixar_backup, name='backup'),
    path('relatorios/', include('relatorios.urls')),
    path('pdv/', include('vendas.urls')),
    path('suprimentos/', include('suprimentos.urls')),
    path('financeiro/', include('financeiro.urls')),
    path('catalogo/', include('catalogo.urls')),
    path('crm/', include('crm.urls')),
    path('notificacoes/', include('notificacoes.urls')),
    path('aprovacoes/', include('aprovacoes.urls')),
    path('cozinha/', include('cozinha.urls')),
    path('cardapio/', cozinha_views.cardapio_publico, name='cardapio_publico'),
    path('cardapio/pedido/', cozinha_views.fazer_pedido, name='fazer_pedido'),
    path('cardapio/acompanhar/<str:codigo>/', cozinha_views.acompanhar_pedido, name='acompanhar_pedido'),
    path('cardapio/m/<uuid:token>/', cozinha_views.confirmar_mesa, name='confirmar_mesa'),
    path('cardapio/m/<uuid:token>/cardapio/', cozinha_views.cardapio_mesa, name='cardapio_mesa'),
    path('cardapio/m/<uuid:token>/chamar/', cozinha_views.chamar_atendente, name='chamar_atendente'),
    path('sw.js', sw_view, name='sw'),
    # Ao acessar a raiz do site, manda direto pro dashboard.
    path('', RedirectView.as_view(url='relatorios/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
