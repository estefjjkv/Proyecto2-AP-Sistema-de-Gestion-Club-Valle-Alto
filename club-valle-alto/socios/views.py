from django.shortcuts import render


def registro_view(request):
    return render(request, 'socios/registro.html')


def inicio_view(request):
    return render(request, 'socios/inicio.html', {'nav_activo': 'inicio'})


def perfil_view(request):
    return render(request, 'socios/perfil.html', {'nav_activo': 'perfil'})


def admin_lista_view(request):
    return render(request, 'socios/admin_lista.html', {'menu_admin': 'socios'})


def admin_detalle_view(request):
    return render(request, 'socios/admin_detalle.html', {'menu_admin': 'socios'})
