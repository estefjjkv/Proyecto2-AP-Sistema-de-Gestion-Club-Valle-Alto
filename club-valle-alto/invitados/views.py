from django.shortcuts import render


def mis_invitados_view(request):
    return render(request, 'invitados/mis_invitados.html', {'nav_activo': 'invitados'})


def recepcion_view(request):
    return render(request, 'invitados/recepcion.html', {'es_recepcion': True})
