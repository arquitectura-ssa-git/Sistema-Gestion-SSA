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

// Time Report: el «+» suma una línea vacía (copia del modelo y avisa al formset que hay una más).
(function () {
  const boton = document.getElementById("agregar-fila");
  const modelo = document.getElementById("fila-nueva");
  if (!boton || !modelo) return;
  const total = document.querySelector("input[name$='-TOTAL_FORMS']");
  const cuerpo = document.querySelector(".tabla-carga tbody");
  boton.addEventListener("click", function () {
    const n = parseInt(total.value, 10);
    const fila = modelo.content.firstElementChild.cloneNode(true);
    fila.innerHTML = fila.innerHTML.replace(/__prefix__/g, n);
    cuerpo.appendChild(fila);
    total.value = n + 1;
    const primero = fila.querySelector("select, input");
    if (primero) primero.focus();
  });
})();

// Time Report: el tachito elimina la fila. Una fila ya guardada se borra al instante (se marca y se guarda el día);
// una nueva o vacía solo se vacía y se oculta (las filas vacías se ignoran al guardar).
document.addEventListener("click", function (e) {
  const boton = e.target.closest(".btn-eliminar-fila");
  if (!boton) return;
  const fila = boton.closest("tr");
  const celda = boton.closest("td");
  if (celda.hasAttribute("data-guardada")) {
    if (!window.confirm("¿Eliminar esta línea del Time Report?")) return;
    celda.querySelector("input[type=checkbox]").checked = true;
    fila.closest("form").submit();
    return;
  }
  fila.querySelectorAll("input, select").forEach(function (c) {
    if (c.type === "checkbox") c.checked = c.defaultChecked;
    else if (c.tagName === "SELECT") Array.from(c.options).forEach(function (o) { o.selected = o.defaultSelected; });
    else if (c.type !== "hidden") c.value = c.defaultValue;
  });
  fila.hidden = true;
});
