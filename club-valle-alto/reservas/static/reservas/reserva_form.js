// Formulario de reserva: filtra servicios por tipo de instalación, ajusta el aforo
// y actualiza el panel de disponibilidad al cambiar instalación o fecha.
(function () {
  "use strict";
  var instalacion = document.getElementById("id_instalacion");
  var fecha = document.getElementById("id_fecha");
  var personas = document.getElementById("id_numero_personas");
  var panel = document.getElementById("panel-disponibilidad");
  if (!instalacion || !fecha) return;

  var CLASES = { libre: "badge--exito", pendiente: "badge--aviso", ocupado: "badge--error", bloqueado: "badge--neutro" };

  function opcionActual() {
    return instalacion.options[instalacion.selectedIndex];
  }

  function filtrarServicios() {
    var opcion = opcionActual();
    var tipo = opcion ? opcion.getAttribute("data-tipo") : null;
    var visibles = 0;
    document.querySelectorAll("[data-servicio]").forEach(function (etiqueta) {
      var casilla = etiqueta.querySelector("input");
      var corresponde = tipo && casilla.getAttribute("data-tipo") === tipo;
      etiqueta.hidden = !corresponde;
      if (!corresponde) casilla.checked = false;
      if (corresponde) visibles++;
    });
    var aviso = document.getElementById("sin-servicios");
    if (aviso) aviso.hidden = !tipo || visibles > 0;
  }

  function actualizarAforo() {
    var opcion = opcionActual();
    var aforo = opcion ? opcion.getAttribute("data-aforo") : null;
    var texto = document.getElementById("aforo-texto");
    if (personas) {
      if (aforo) personas.max = aforo; else personas.removeAttribute("max");
    }
    if (texto) texto.textContent = aforo ? "Aforo máximo: " + aforo + " persona" + (aforo === "1" ? "" : "s") : "";
  }

  function fila(franja, ultima) {
    var div = document.createElement("div");
    div.style.cssText = "display:flex;align-items:center;justify-content:space-between;padding:0.7rem 0;" +
      (ultima ? "" : "border-bottom:1px solid #EAEeea");
    var horas = document.createElement("span");
    horas.textContent = franja.inicio + " - " + franja.fin;
    var estado = document.createElement("span");
    estado.className = "badge " + (CLASES[franja.estado] || "badge--neutro");
    estado.textContent = franja.etiqueta;
    div.appendChild(horas);
    div.appendChild(estado);
    return div;
  }

  function cargarDisponibilidad() {
    if (!panel) return;
    var subtitulo = document.getElementById("disp-subtitulo");
    var lista = document.getElementById("disp-franjas");
    if (!instalacion.value || !fecha.value) {
      subtitulo.textContent = "Elija instalación y fecha";
      lista.replaceChildren();
      return;
    }
    var params = new URLSearchParams({ instalacion: instalacion.value, fecha: fecha.value });
    if (panel.dataset.excluir) params.set("excluir", panel.dataset.excluir);
    fetch(panel.dataset.url + "?" + params.toString(), { headers: { Accept: "application/json" } })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
      .then(function (datos) {
        subtitulo.textContent = datos.instalacion + " · " + datos.fecha;
        lista.replaceChildren();
        if (!datos.franjas.length) {
          var vacio = document.createElement("p");
          vacio.style.cssText = "color:var(--texto-suave);font-size:0.86rem";
          vacio.textContent = "La instalación no está disponible.";
          lista.appendChild(vacio);
        }
        datos.franjas.forEach(function (f, i) { lista.appendChild(fila(f, i === datos.franjas.length - 1)); });
      })
      .catch(function () {
        subtitulo.textContent = "No se pudo consultar la disponibilidad.";
      });
  }

  instalacion.addEventListener("change", function () {
    filtrarServicios();
    actualizarAforo();
    cargarDisponibilidad();
  });
  fecha.addEventListener("change", cargarDisponibilidad);

  filtrarServicios();
  actualizarAforo();
})();
