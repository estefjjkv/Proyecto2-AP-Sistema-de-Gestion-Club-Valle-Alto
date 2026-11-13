from django.urls import path
from . import views

app_name = 'invitados'

urlpatterns = [
    path('', views.mis_invitados_view, name='mis_invitados'),
    path('recepcion/', views.recepcion_view, name='recepcion'),
]
