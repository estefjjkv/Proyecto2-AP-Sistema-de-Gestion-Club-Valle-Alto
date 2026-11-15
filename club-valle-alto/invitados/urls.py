from django.urls import path
from guests import views
app_name = "invitados"
urlpatterns = [
    path("", views.mine, name="mis_invitados"),
    path("recepcion/", views.reception, name="recepcion"),
    path("recepcion/<str:pk>/ingreso/", views.arrival, name="ingreso"),
]
