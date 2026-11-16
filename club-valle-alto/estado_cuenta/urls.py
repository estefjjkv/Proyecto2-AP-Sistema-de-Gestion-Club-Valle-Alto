from django.urls import path
from . import views

app_name = 'estado_cuenta'

urlpatterns = [
    # Socio
    path('', views.mi_estado_view, name='mi_estado'),
    path('historial/', views.historial_view, name='historial'),
    path('imprimir/<str:periodo>/', views.imprimir_view, name='imprimir'),
    # Administración
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('gestion/generar/', views.admin_generar_view, name='generar'),
    path('gestion/<str:cedula>/', views.admin_detalle_view, name='admin_detalle'),
    path('gestion/<str:cedula>/imprimir/<str:periodo>/', views.admin_imprimir_view, name='admin_imprimir'),
    path('pagos/', views.admin_pagos_view, name='pagos'),
]
