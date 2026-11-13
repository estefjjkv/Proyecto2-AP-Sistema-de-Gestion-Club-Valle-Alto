from django.urls import path
from . import views

app_name = 'notificaciones'

urlpatterns = [
    path('', views.centro_view, name='centro'),
]
