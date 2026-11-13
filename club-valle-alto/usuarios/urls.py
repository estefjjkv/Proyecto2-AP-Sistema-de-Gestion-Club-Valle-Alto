from django.urls import path
from . import views

app_name = 'usuarios'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('recuperar/', views.recuperar_view, name='recuperar'),
    path('salir/', views.salir_view, name='salir'),
]
