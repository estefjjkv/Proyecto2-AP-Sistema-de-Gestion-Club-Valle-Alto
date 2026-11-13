from django.urls import path
from . import views

app_name = 'membresias'

urlpatterns = [
    path('', views.mi_membresia_view, name='mi_membresia'),
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('gestion/formulario/', views.admin_form_view, name='formulario'),
]
