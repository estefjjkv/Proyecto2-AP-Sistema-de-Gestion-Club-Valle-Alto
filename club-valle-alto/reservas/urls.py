from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    path('', views.mis_reservas_view, name='mis_reservas'),
    path('nueva/', views.nueva_reserva_view, name='nueva'),
    path('detalle/', views.detalle_reserva_view, name='detalle'),
    path('calendario/', views.admin_calendario_view, name='calendario'),
    path('administrar/', views.admin_detalle_view, name='administrar'),
]
