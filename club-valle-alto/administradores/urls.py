from django.urls import path
from . import views

app_name = 'administradores'

urlpatterns = [
    path('', views.gestion_view, name='gestion'),
    path('panel/', views.panel_view, name='panel'),
]
