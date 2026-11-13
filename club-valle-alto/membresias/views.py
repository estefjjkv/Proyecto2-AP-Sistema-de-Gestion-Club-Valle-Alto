from django.shortcuts import render


def mi_membresia_view(request):
    return render(request, 'membresias/mi_membresia.html', {'nav_activo': 'membresia'})


def admin_lista_view(request):
    return render(request, 'membresias/admin_lista.html', {'menu_admin': 'membresias'})


def admin_form_view(request):
    return render(request, 'membresias/admin_form.html', {'menu_admin': 'membresias'})
