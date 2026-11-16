(function () {
  "use strict";

  // 1. Abrir y cerrar modales: <button data-abrir-modal="id_modal"> / <button data-cerrar-modal>
  document.querySelectorAll("[data-abrir-modal]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var id = btn.getAttribute("data-abrir-modal");
      var modal = document.getElementById(id);
      if (modal) {
        modal.classList.add("abierto");
      }
    });
  });

  document.querySelectorAll("[data-cerrar-modal]").forEach(function (btn) {
    btn.addEventListener("click", function (e) {
      e.preventDefault();
      var fondo = btn.closest(".modal-fondo");
      if (fondo) {
        fondo.classList.remove("abierto");
      }
    });
  });

  document.querySelectorAll(".modal-fondo").forEach(function (fondo) {
    fondo.addEventListener("click", function (e) {
      if (e.target === fondo) {
        fondo.classList.remove("abierto");
      }
    });
  });

  // Cerrar modal con tecla Escape
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      document.querySelectorAll(".modal-fondo.abierto").forEach(function (m) {
        m.classList.remove("abierto");
      });
      var guia = document.getElementById("guia-prototipo");
      if (guia) guia.classList.remove("abierto");
    }
  });

  // 2. Pestañas interactivas (ej. Mis reservas: Activas / Finalizadas / Canceladas)
  document.querySelectorAll("[data-tab-grupo]").forEach(function (contenedor) {
    var botones = contenedor.querySelectorAll("[data-tab]");
    botones.forEach(function (btn) {
      btn.addEventListener("click", function () {
        var valor = btn.getAttribute("data-tab");
        botones.forEach(function (b) { b.classList.remove("activo"); });
        btn.classList.add("activo");
        document.querySelectorAll("[data-fila-estado]").forEach(function (fila) {
          var est = fila.getAttribute("data-fila-estado");
          fila.style.display = (valor === "todas" || est === valor) ? "" : "none";
        });
      });
    });
  });

  // 3. Guía flotante de las 29 pantallas del prototipo
  var guia = document.getElementById("guia-prototipo");
  var btnGuia = document.getElementById("btn-guia-prototipo");
  if (guia && btnGuia) {
    btnGuia.addEventListener("click", function () {
      guia.classList.toggle("abierto");
    });
  }

  // 4. Confirmar contraseña: <input data-coincide="id_de_la_clave">
  document.querySelectorAll("[data-coincide]").forEach(function (campo) {
    var origen = document.getElementById(campo.getAttribute("data-coincide"));
    if (!origen) return;
    function revisar() {
      campo.setCustomValidity(
        campo.value && campo.value !== origen.value ? "Las contraseñas no coinciden." : ""
      );
    }
    campo.addEventListener("input", revisar);
    origen.addEventListener("input", revisar);
  });

  // Las acciones persisten en el servidor, no se simulan visualmente.
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.dataset.confirmar)) event.preventDefault();
    });
  });
})();
