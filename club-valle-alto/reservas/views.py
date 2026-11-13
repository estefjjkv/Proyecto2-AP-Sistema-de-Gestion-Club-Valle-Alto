from django.shortcuts import render


def mis_reservas_view(request):
    return render(request, 'reservas/mis_reservas.html', {'nav_activo': 'reservas'})


def nueva_reserva_view(request):
    return render(request, 'reservas/nueva_reserva.html', {'nav_activo': 'reservas'})


def detalle_reserva_view(request):
    return render(request, 'reservas/detalle_reserva.html', {'nav_activo': 'reservas'})


def admin_calendario_view(request):
    return render(request, 'reservas/admin_calendario.html', {'menu_admin': 'reservas'})


def admin_detalle_view(request):
    return render(request, 'reservas/admin_detalle.html', {'menu_admin': 'reservas'})
