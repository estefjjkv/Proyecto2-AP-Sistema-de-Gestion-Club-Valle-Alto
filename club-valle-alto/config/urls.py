"""
URL configuration for Club Valle Alto.
"""
from django.contrib import admin
from django.urls import path, include
from usuarios import views as usuarios_views

urlpatterns = [
    path('', usuarios_views.login_view, name='raiz'),
    path('admin/', admin.site.urls),
    path('usuarios/', include('usuarios.urls')),
    path('socios/', include('socios.urls')),
    path('membresias/', include('membresias.urls')),
    path('invitados/', include('invitados.urls')),
    path('instalaciones/', include('instalaciones.urls')),
    path('reservas/', include('reservas.urls')),
    path('estado-cuenta/', include('estado_cuenta.urls')),
    path('notificaciones/', include('notificaciones.urls')),
    path('administradores/', include('administradores.urls')),
]
