from django.urls import path
from . import views

app_name = 'instalaciones'

urlpatterns = [
    path('', views.catalogo_view, name='catalogo'),
    path('gestion/', views.admin_lista_view, name='gestion'),
    path('gestion/nueva/', views.admin_form_view, name='nueva'),
    path('gestion/<str:codigo>/', views.admin_form_view, name='editar'),
    path('servicios/', views.admin_servicios_view, name='servicios'),
    path('servicios/<str:codigo>/', views.admin_servicios_view, name='servicio_editar'),
    path('bloqueos/', views.admin_bloqueos_view, name='bloqueos'),
    path('bloqueos/<int:pk>/eliminar/', views.admin_bloqueo_eliminar_view, name='bloqueo_eliminar'),
    path('ocupacion/', views.admin_ocupacion_view, name='ocupacion'),
    path('reportes/', views.admin_reportes_view, name='reportes'),
]
