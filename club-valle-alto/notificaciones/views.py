from django.shortcuts import render


def centro_view(request):
    return render(request, 'notificaciones/centro.html', {'menu_admin': 'notificaciones'})
