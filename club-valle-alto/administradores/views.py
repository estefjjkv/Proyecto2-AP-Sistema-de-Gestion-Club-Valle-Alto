from django.shortcuts import render


def panel_view(request):
    return render(request, 'administradores/panel.html', {'menu_admin': 'inicio'})


def gestion_view(request):
    return render(request, 'administradores/gestion.html', {'menu_admin': 'administradores'})
