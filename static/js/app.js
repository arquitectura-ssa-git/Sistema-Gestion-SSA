// Pide confirmación en los formularios con data-confirmar="mensaje".
document.addEventListener("submit", function (e) {
  const mensaje = e.target.dataset.confirmar;
  if (mensaje && !window.confirm(mensaje)) {
    e.preventDefault();
  }
});

// Zona para arrastrar y soltar archivos sobre un <input type="file">.
document.querySelectorAll("[data-zona-soltar]").forEach(function (zona) {
  const input = document.getElementById(zona.dataset.zonaSoltar);
  const lista = zona.querySelector("[data-lista-archivos]");
  if (!input) return;

  function mostrar() {
    if (!lista) return;
    lista.innerHTML = "";
    Array.from(input.files).forEach(function (f) {
      const li = document.createElement("li");
      li.textContent = f.name + " (" + (f.size / 1048576).toFixed(1) + " MB)";
      lista.appendChild(li);
    });
  }

  zona.addEventListener("click", function () { input.click(); });
  input.addEventListener("change", mostrar);
  ["dragenter", "dragover"].forEach(function (ev) {
    zona.addEventListener(ev, function (e) { e.preventDefault(); zona.classList.add("encima"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    zona.addEventListener(ev, function (e) { e.preventDefault(); zona.classList.remove("encima"); });
  });
  zona.addEventListener("drop", function (e) {
    input.files = e.dataTransfer.files;
    mostrar();
  });
});

// Tabla editable de tareas con incidencia: agregar/quitar filas y sumar en vivo.
document.querySelectorAll("[data-tareas]").forEach(function (caja) {
  const prefijo = caja.dataset.prefijo;
  const total = caja.querySelector("#id_" + prefijo + "-TOTAL_FORMS");
  const filas = caja.querySelector("[data-filas]");
  const molde = caja.querySelector("[data-fila-vacia]");

  function numero(input) {
    const v = parseFloat(((input && input.value) || "").replace(",", "."));
    return isNaN(v) ? 0 : v;
  }

  function recalcular() {
    let suma = 0, avance = 0, n = 0;
    filas.querySelectorAll("[data-fila]").forEach(function (fila) {
      if (fila.classList.contains("d-none")) return;
      n += 1;
      fila.querySelector("[data-numero]").textContent = n;
      const inc = numero(fila.querySelector("[data-incidencia]"));
      suma += inc;
      const av = fila.querySelector("[data-avance]");
      if (av) {
        const aporte = inc * Math.min(Math.max(numero(av), 0), 100) / 100;
        avance += aporte;
        fila.querySelector("[data-aporte]").textContent = aporte.toFixed(2).replace(".", ",") + " %";
      }
    });
    const ok = Math.abs(suma - 100) < 0.005;
    const totalInc = caja.querySelector("[data-total-incidencia]");
    totalInc.textContent = suma.toFixed(2).replace(".", ",").replace(",00", "");
    totalInc.className = ok ? "text-success" : "text-danger";
    caja.querySelector("[data-aviso-total]").textContent = ok ? "" : (suma < 100 ? "(faltan " : "(sobran ") + Math.abs(100 - suma).toFixed(2).replace(".", ",") + ")";
    caja.querySelector("[data-aviso-total]").className = "small " + (ok ? "" : "text-danger");
    const totalAv = caja.querySelector("[data-total-avance]");
    if (totalAv) totalAv.textContent = (suma > 0 ? avance * 100 / suma : 0).toFixed(1).replace(".", ",");
  }

  caja.querySelector("[data-agregar-tarea]").addEventListener("click", function () {
    const indice = parseInt(total.value, 10);
    const html = molde.innerHTML.replace(/__prefix__/g, indice);
    filas.insertAdjacentHTML("beforeend", html);
    total.value = indice + 1;
    const nueva = filas.lastElementChild;
    nueva.querySelector("input[type=text]").focus();
    recalcular();
  });

  filas.addEventListener("click", function (e) {
    const boton = e.target.closest("[data-quitar-tarea]");
    if (!boton) return;
    const fila = boton.closest("[data-fila]");
    const borrar = fila.querySelector("input[name$='-DELETE']");
    if (borrar) borrar.checked = true;
    fila.classList.add("d-none");
    recalcular();
  });

  filas.addEventListener("input", recalcular);
  recalcular();
});
