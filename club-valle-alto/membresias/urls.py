from django.urls import path
from memberships import views
app_name = "membresias"
urlpatterns = [
    path("", views.mine, name="mi_membresia"),
    path("gestion/", views.listing, name="gestion"),
    path("gestion/formulario/", views.edit, name="formulario"),
    path("gestion/<str:pk>/", views.edit, name="editar"),
    path("tipos/", views.types, name="tipos"),
    path("tipos/<str:pk>/", views.types, name="tipo_editar"),
    path("<str:membership_id>/beneficiarios/nuevo/", views.beneficiary, name="beneficiario_nuevo"),
    path("<str:membership_id>/beneficiarios/<str:pk>/", views.beneficiary, name="beneficiario_editar"),
    path("<str:membership_id>/beneficiarios/<str:pk>/eliminar/", views.delete_beneficiary, name="beneficiario_eliminar"),
]
