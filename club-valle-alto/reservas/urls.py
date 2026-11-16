from django.urls import path
from . import views

app_name = 'reservas'

urlpatterns = [
    # Socio
    path('', views.mis_reservas_view, name='mis_reservas'),
    path('nueva/', views.nueva_reserva_view, name='nueva'),
    path('disponibilidad/', views.disponibilidad_view, name='disponibilidad'),
    path('<int:pk>/', views.detalle_reserva_view, name='detalle'),
    path('<int:pk>/modificar/', views.modificar_reserva_view, name='modificar'),
    path('<int:pk>/cancelar/', views.cancelar_reserva_view, name='cancelar'),
    # Administración
    path('calendario/', views.calendario_view, name='calendario'),
    path('administrar/nueva/', views.admin_nueva_view, name='admin_nueva'),
    path('administrar/<int:pk>/', views.administrar_view, name='administrar'),
    path('administrar/<int:pk>/cancelar/', views.admin_cancelar_view, name='admin_cancelar'),
]
