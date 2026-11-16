from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from accounts.permissions import member_only, permitted
from socios.models import Socio
from .forms import FiltroForm, GenerarForm, PagoForm
from .models import Cargo, EstadoCuenta, Pago, VEstadoCuentaResumen, VSocioMoroso
from .services import colones, estado_resumen, estado_visible, generar_estados, nombre_periodo, registrar_pago


def _periodo(texto):
    """'2026-11' o '2026-11-01' -> date(2026, 11, 1); None si no es válido."""
    try:
        return date.fromisoformat(texto[:7] + "-01") if texto else None
    except ValueError:
        return None


def _resumenes(socio_id):
    hoy = timezone.localdate()
    filas = list(VEstadoCuentaResumen.objects.filter(cedula_socio=socio_id).order_by("-periodo"))
    for fila in filas:
        fila.estado = estado_resumen(fila, hoy)
        fila.saldo = fila.pendiente + fila.vencido
    return filas


def _detalle(socio_id, periodo):
    """Cargos de un periodo con su estado visible y totales; None si el periodo no existe."""
    estado = EstadoCuenta.objects.filter(socio_id=socio_id, periodo=periodo).first()
    if estado is None:
        return None
    hoy = timezone.localdate()
    cargos = list(Cargo.objects.filter(socio_id=socio_id, periodo=periodo)
                  .select_related("tipo", "pago_detalle__pago").order_by("tipo_id", "pk"))
    for cargo in cargos:
        cargo.estado_mostrado = estado_visible(cargo, hoy)
    total = sum(c.monto for c in cargos)
    pagado = sum(c.monto for c in cargos if c.estado_id == "PAGADO")
    return {"estado": estado, "cargos": cargos, "total": total, "pagado": pagado, "pendiente": total - pagado,
            "periodo": periodo}


def _elegir_periodo(request, resumenes):
    pedido = _periodo(request.GET.get("periodo"))
    disponibles = [r.periodo for r in resumenes]
    if pedido in disponibles:
        return pedido
    actual = timezone.localdate().replace(day=1)
    anteriores = [p for p in disponibles if p <= actual]
    return anteriores[0] if anteriores else (disponibles[-1] if disponibles else None)


# --- Socio --------------------------------------------------------------

@member_only
def mi_estado_view(request):
    resumenes = _resumenes(request.user.pk)
    periodo = _elegir_periodo(request, resumenes)
    return render(request, "estado_cuenta/mi_estado.html", {
        "resumenes": resumenes, "detalle": _detalle(request.user.pk, periodo) if periodo else None,
        "nav_activo": "estado_cuenta"})


@member_only
def historial_view(request):
    return render(request, "estado_cuenta/historial.html", {"resumenes": _resumenes(request.user.pk),
                  "nav_activo": "estado_cuenta"})


def _impresion(request, socio, periodo_texto):
    periodo = _periodo(periodo_texto)
    detalle = _detalle(socio.pk, periodo) if periodo else None
    if detalle is None:
        raise Http404("No existe ese estado de cuenta.")
    return render(request, "estado_cuenta/imprimir.html", {"socio": socio, "detalle": detalle,
                  "emitido": timezone.localtime()})


@member_only
def imprimir_view(request, periodo):
    return _impresion(request, get_object_or_404(Socio, pk=request.user.pk), periodo)


# --- Administración -------------------------------------------------------

@permitted("manage_billing")
def admin_lista_view(request):
    actual = timezone.localdate().replace(day=1)
    form = FiltroForm(request.GET if "periodo" in request.GET else {"periodo": actual.isoformat()})
    periodo = form.cleaned_data["periodo"] if form.is_valid() else actual
    q = form.cleaned_data.get("q", "").strip() if form.is_valid() else ""
    filtro_estado = form.cleaned_data.get("estado") if form.is_valid() else ""

    resumenes = VEstadoCuentaResumen.objects.filter(periodo=periodo)
    socios = Socio.objects.filter(cedula__in=resumenes.values("cedula_socio"))
    if q:
        socios = socios.filter(Q(nombre_completo__icontains=q) | Q(cedula__icontains=q))
    nombres = dict(socios.values_list("cedula", "nombre_completo"))
    montos = {}
    for fila in Cargo.objects.filter(periodo=periodo).values("socio_id", "tipo_id").annotate(suma=Sum("monto")):
        montos[(fila["socio_id"], fila["tipo_id"])] = fila["suma"]

    hoy, filas = timezone.localdate(), []
    for r in resumenes:
        if r.cedula_socio not in nombres:
            continue
        estado = estado_resumen(r, hoy)
        if filtro_estado and estado != filtro_estado:
            continue
        filas.append({"cedula": r.cedula_socio, "nombre": nombres[r.cedula_socio], "resumen": r, "estado": estado,
                      "saldo": r.pendiente + r.vencido, "cuota": montos.get((r.cedula_socio, "CUOTA_MEMBRESIA"), 0),
                      "servicios": montos.get((r.cedula_socio, "SERVICIO_ADICIONAL"), 0)})
    filas.sort(key=lambda f: f["nombre"])
    return render(request, "estado_cuenta/admin_lista.html", {
        "form": form, "periodo": periodo, "filas": filas, "generar": GenerarForm(initial={"periodo": periodo.isoformat()}),
        "menu_admin": "cobros"})


@permitted("manage_billing")
@require_POST
def admin_generar_view(request):
    form = GenerarForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Elija un periodo válido.")
        return redirect("estado_cuenta:gestion")
    periodo = form.cleaned_data["periodo"]
    cuotas = generar_estados(periodo)
    messages.success(request, f"Periodo {nombre_periodo(periodo)}: {cuotas} cuota(s) nueva(s) generada(s)."
                     if cuotas else f"Periodo {nombre_periodo(periodo)}: no había cuotas nuevas por generar.")
    return redirect(reverse("estado_cuenta:gestion") + f"?periodo={periodo.isoformat()}")


@permitted("manage_billing")
def admin_detalle_view(request, cedula):
    socio = get_object_or_404(Socio, pk=cedula)
    resumenes = _resumenes(socio.pk)
    periodo = _elegir_periodo(request, resumenes)
    return render(request, "estado_cuenta/admin_detalle.html", {
        "socio": socio, "resumenes": resumenes, "detalle": _detalle(socio.pk, periodo) if periodo else None,
        "menu_admin": "cobros"})


@permitted("manage_billing")
def admin_imprimir_view(request, cedula, periodo):
    return _impresion(request, get_object_or_404(Socio, pk=cedula), periodo)


@permitted("manage_billing")
@require_http_methods(["GET", "POST"])
def admin_pagos_view(request):
    socio_id = request.POST.get("socio") or request.GET.get("socio") or None
    form = PagoForm(request.POST or None, socio_id=socio_id,
                    initial={"socio": socio_id, "fecha_pago": timezone.localdate()})
    if request.method == "POST" and form.is_valid():
        datos = form.cleaned_data
        try:
            pago = registrar_pago(datos["socio"].pk, datos["cargos"], datos["fecha_pago"], datos["referencia"], request.user)
        except ValidationError as error:
            form.add_error(None, " ".join(error.messages))
        else:
            messages.success(request, f"Pago #{pago.pk} registrado por {colones(pago.monto)}.")
            return redirect(reverse("estado_cuenta:pagos") + f"?socio={pago.socio_id}")
    socio = Socio.objects.filter(pk=socio_id).first() if socio_id else None
    return render(request, "estado_cuenta/admin_pagos.html", {
        "form": form, "socio": socio,
        "morosos": VSocioMoroso.objects.order_by("-dias_atraso_max", "-monto_adeudado"),
        "pagos": Pago.objects.select_related("socio", "admin").prefetch_related("detalles__cargo")[:10],
        "menu_admin": "cobros"})
