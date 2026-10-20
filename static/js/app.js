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
