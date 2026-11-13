from django.shortcuts import render


def mi_estado_view(request):
    return render(request, 'estado_cuenta/mi_estado.html', {'nav_activo': 'estado_cuenta'})


def historial_view(request):
    return render(request, 'estado_cuenta/historial.html', {'nav_activo': 'estado_cuenta'})


def admin_lista_view(request):
    return render(request, 'estado_cuenta/admin_lista.html', {'menu_admin': 'cobros'})


def admin_pagos_view(request):
    return render(request, 'estado_cuenta/admin_pagos.html', {'menu_admin': 'cobros'})
