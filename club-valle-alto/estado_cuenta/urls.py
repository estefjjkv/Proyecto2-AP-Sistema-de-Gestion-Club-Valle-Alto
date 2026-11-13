from django.urls import path
from . import views

app_name = 'estado_cuenta'

urlpatterns = [
    path('', views.mi_estado_view, name='mi_estado'),
    path('historial/', views.historial_view, name='historial'),
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('pagos/', views.admin_pagos_view, name='pagos'),
]
