from django.shortcuts import render


def catalogo_view(request):
    return render(request, 'instalaciones/catalogo.html', {'nav_activo': 'instalaciones'})


def admin_lista_view(request):
    return render(request, 'instalaciones/admin_lista.html', {'menu_admin': 'instalaciones'})


def admin_bloqueos_view(request):
    return render(request, 'instalaciones/admin_bloqueos.html', {'menu_admin': 'instalaciones'})


def admin_ocupacion_view(request):
    return render(request, 'instalaciones/admin_ocupacion.html', {'menu_admin': 'instalaciones'})


def admin_reportes_view(request):
    return render(request, 'instalaciones/admin_reportes.html', {'menu_admin': 'instalaciones'})
