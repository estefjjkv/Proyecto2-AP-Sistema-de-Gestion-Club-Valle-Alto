from django.urls import path
from accounts import views
app_name = "administradores"
urlpatterns = [
    path("", views.admin_users, name="gestion"),
    path("<str:pk>/editar/", views.admin_users, name="editar"),
    path("<str:pk>/clave/", views.admin_password, name="clave"),
    path("panel/", views.dashboard, name="panel"),
]
