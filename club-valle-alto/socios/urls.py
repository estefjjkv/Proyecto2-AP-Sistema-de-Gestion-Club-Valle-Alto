from django.urls import path
from . import views

app_name = 'socios'

urlpatterns = [
    path('', views.admin_lista_view, name='lista'),
    path('registro/', views.registro_view, name='registro'),
    path('inicio/', views.inicio_view, name='inicio'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('gestion/detalle/', views.admin_detalle_view, name='gestion_detalle'),
]
