from django.shortcuts import render, redirect


def login_view(request):
    return render(request, 'usuarios/login.html')


def recuperar_view(request):
    return render(request, 'usuarios/recuperar.html')


def salir_view(request):
    return redirect('usuarios:login')
