from django.urls import path
from accounts import views
app_name = "socios"
urlpatterns = [
    path("", views.member_list, name="lista"),
    path("registro/", views.register, name="registro"),
    path("inicio/", views.home, name="inicio"),
    path("perfil/", views.profile, name="perfil"),
    path("gestion/", views.member_list, name="gestion"),
    path("gestion/<str:pk>/", views.member_detail, name="gestion_detalle"),
]
