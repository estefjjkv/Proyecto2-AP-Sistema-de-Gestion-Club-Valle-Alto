from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.views import PasswordResetCompleteView
from accounts.views import ClubLoginView, recover, logout_view, reset_confirm
app_name = "usuarios"
urlpatterns = [
    path("login/", ClubLoginView.as_view(), name="login"),
    path("salir/", logout_view, name="salir"),
    path("recuperar/", recover, name="recuperar"),
    path("recuperar/enviado/", TemplateView.as_view(template_name="usuarios/reset_sent.html"), name="recuperar_enviado"),
    path("restablecer/<str:token>/", reset_confirm, name="reset_confirm"),
    path("restablecida/", PasswordResetCompleteView.as_view(template_name="usuarios/reset_complete.html"), name="reset_complete"),
]
