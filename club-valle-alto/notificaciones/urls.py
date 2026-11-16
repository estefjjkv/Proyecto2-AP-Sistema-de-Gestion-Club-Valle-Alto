from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.centro_view, name='centro'),
    path('<int:pk>/reenviar/', views.reenviar_view, name='reenviar'),
    path('plantillas/<str:tipo>/', views.plantilla_view, name='plantilla'),
]
