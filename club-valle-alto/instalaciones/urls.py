from django.urls import path
from . import views

app_name = 'instalaciones'

urlpatterns = [
    path('', views.catalogo_view, name='catalogo'),
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('bloqueos/', views.admin_bloqueos_view, name='bloqueos'),
    path('ocupacion/', views.admin_ocupacion_view, name='ocupacion'),
    path('reportes/', views.admin_reportes_view, name='reportes'),
]
