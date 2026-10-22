// Listado de tareas en árbol (etapas → rubros → ítems) con incidencias y avance.
//
// 1) Editor: [data-editor-tareas] arma la tabla editable a partir del JSON del <input name="estructura">
//    y lo vuelve a escribir al enviar el formulario. Al cambiar una incidencia, agregar o quitar una fila,
//    las demás del mismo grupo se reacomodan para que sigan sumando 100%.
// 2) Barras de avance: [data-barra-avance] guarda el avance al soltar la barra y actualiza los totales.
(function () {
  "use strict";

  const NOMBRE = { etapa: "Etapa", rubro: "Rubro", item: "Ítem" };
  const HIJO = { etapa: "rubro", rubro: "item" };

  function num(v) {
    const n = parseFloat(String(v).replace(",", "."));
    return isFinite(n) ? n : 0;
  }
  function fmt(n, dec) {
    return n.toFixed(dec === undefined ? 1 : dec).replace(".", ",").replace(/,0+$/, "").replace(/(,\d*?)0+$/, "$1");
  }
  function esc(t) {
    const d = document.createElement("div");
    d.textContent = t == null ? "" : String(t);
    return d.innerHTML;
  }

  // --- Reparto de incidencias dentro de un grupo -------------------------------------------------
  function suma(lista) { return lista.reduce((a, n) => a + num(n.incidencia), 0); }

  // Fija la incidencia de `nodo` y reparte el resto entre sus hermanos, en proporción a lo que tenían.
  function fijar(hermanos, nodo, valor) {
    const otros = hermanos.filter((h) => h !== nodo);
    if (!otros.length) { nodo.incidencia = 100; return; }
    valor = Math.min(Math.max(valor, 0.1), 99.9);
    nodo.incidencia = valor;
    const resto = 100 - valor;
    const sumaOtros = suma(otros);
    otros.forEach((o) => { o.incidencia = sumaOtros > 0 ? num(o.incidencia) * resto / sumaOtros : resto / otros.length; });
  }
  function normalizar(hermanos) {
    const s = suma(hermanos);
    if (!hermanos.length) return;
    hermanos.forEach((h) => { h.incidencia = s > 0 ? num(h.incidencia) * 100 / s : 100 / hermanos.length; });
  }

  function avanceDe(n) {
    if (!n.hijos || !n.hijos.length) return num(n.avance);
    const s = suma(n.hijos);
    return s > 0 ? n.hijos.reduce((a, h) => a + num(h.incidencia) * avanceDe(h), 0) / s : 0;
  }

  // --- Editor -------------------------------------------------------------------------------------
  function Editor(caja) {
    const form = caja.closest("form");
    const campo = form.querySelector("input[name=estructura]");
    const conAvance = caja.dataset.conAvance === "1";
    const cuerpo = caja.querySelector("[data-cuerpo]");
    let datos;
    try { datos = JSON.parse(campo.value || "[]"); } catch (e) { datos = []; }
    // Listados con código propio (ej. de un certificado: 1.10.15) necesitan la columna de número más ancha.
    (function hayCodigos(lista) {
      lista.forEach((n) => { if (n.codigo) caja.classList.add("con-codigos"); hayCodigos(n.hijos || []); });
    })(datos);
    let sucio = false;

    function marcarSucio() { sucio = true; }

    function fila(n, hermanos, padre, nivel, numero, pesoTotal) {
      const hoja = !n.hijos || !n.hijos.length;
      const tr = document.createElement("div");
      tr.className = "te-fila te-" + n.tipo;
      const puedeHijo = HIJO[n.tipo];
      const idx = hermanos.indexOf(n);
      const plegable = n.tipo === "rubro" && !hoja;
      tr.innerHTML =
        '<div class="te-num">' + (plegable ? '<button type="button" class="btn-plegar" data-a="plegar" aria-expanded="' +
          (n._plegado ? "false" : "true") + '" title="Contraer / expandir ítems"><i class="bi bi-chevron-down"></i></button>' : "") +
          esc(n.codigo || numero) + "</div>" +
        '<div class="te-nombre"><input type="text" class="form-control form-control-sm" maxlength="300" placeholder="Nombre ' +
          (n.tipo === "etapa" ? "de la etapa" : n.tipo === "rubro" ? "del rubro" : "del ítem") + '" value="' + esc(n.nombre) + '"></div>' +
        '<div class="te-inc"><div class="input-group input-group-sm"><input type="number" class="form-control" min="0.1" max="100" step="0.1" value="' +
          fmt(num(n.incidencia), 2).replace(",", ".") + '"' + (hermanos.length === 1 ? " disabled" : "") +
          ' title="Incidencia dentro de su grupo"><span class="input-group-text">%</span></div>' +
          '<div class="te-total" title="Peso en el total">' + fmt(pesoTotal, 2) + "% del total</div></div>" +
        (conAvance ? '<div class="te-avance">' + (hoja
          ? '<input type="range" class="form-range" min="0" max="100" step="5" value="' + num(n.avance) + '"><span class="te-av-num">' + num(n.avance) + "%</span>"
          : '<span class="te-av-calc">' + fmt(avanceDe(n)) + "%</span>") + "</div>" : "") +
        '<div class="te-acciones btn-group btn-group-sm">' +
          '<button type="button" class="btn btn-outline-secondary" data-a="subir" title="Subir"' + (idx === 0 ? " disabled" : "") + '><i class="bi bi-arrow-up"></i></button>' +
          '<button type="button" class="btn btn-outline-secondary" data-a="bajar" title="Bajar"' + (idx === hermanos.length - 1 ? " disabled" : "") + '><i class="bi bi-arrow-down"></i></button>' +
          (puedeHijo ? '<button type="button" class="btn btn-outline-dark" data-a="hijo" title="Agregar ' + NOMBRE[puedeHijo].toLowerCase() + '"><i class="bi bi-plus-lg"></i> ' + NOMBRE[puedeHijo] + "</button>" : "") +
          '<button type="button" class="btn btn-outline-danger" data-a="quitar" title="Quitar"><i class="bi bi-trash"></i></button>' +
        "</div>";

      const [inNombre] = tr.querySelectorAll(".te-nombre input");
      inNombre.addEventListener("input", () => { n.nombre = inNombre.value; marcarSucio(); });
      const inInc = tr.querySelector(".te-inc input");
      inInc.addEventListener("change", () => { fijar(hermanos, n, num(inInc.value)); marcarSucio(); dibujar(); });
      const rango = tr.querySelector("input[type=range]");
      if (rango) {
        rango.addEventListener("input", () => {
          n.avance = parseInt(rango.value, 10);
          tr.querySelector(".te-av-num").textContent = n.avance + "%";
          marcarSucio();
        });
        rango.addEventListener("change", dibujar);
      }
      const btnPlegar = tr.querySelector("[data-a=plegar]");
      if (btnPlegar) btnPlegar.addEventListener("click", () => { n._plegado = !n._plegado; dibujar(); });
      tr.querySelector(".te-acciones").addEventListener("click", (e) => {
        const b = e.target.closest("button[data-a]");
        if (!b) return;
        const a = b.dataset.a;
        if (a === "subir" || a === "bajar") {
          const j = idx + (a === "subir" ? -1 : 1);
          [hermanos[idx], hermanos[j]] = [hermanos[j], hermanos[idx]];
        } else if (a === "hijo") {
          n.hijos = n.hijos || [];
          const nuevo = { tipo: HIJO[n.tipo], nombre: "", incidencia: 0, avance: hoja ? num(n.avance) : 0, hijos: [] };
          n.hijos.push(nuevo);
          n._plegado = false;
          fijar(n.hijos, nuevo, 100 / n.hijos.length);
          dibujar(nuevo);
          marcarSucio();
          return;
        } else if (a === "quitar") {
          const cuantos = contar(n) - 1;
          const msg = "¿Quitar " + NOMBRE[n.tipo].toLowerCase() + " «" + (n.nombre || "sin nombre") + "»" +
            (cuantos ? " y lo que tiene adentro (" + cuantos + ")" : "") + "?";
          if ((n.nombre || cuantos) && !window.confirm(msg)) return;
          hermanos.splice(idx, 1);
          normalizar(hermanos);
        }
        marcarSucio();
        dibujar();
      });
      return tr;
    }

    function contar(n) { return 1 + (n.hijos || []).reduce((a, h) => a + contar(h), 0); }

    let enfocar = null;
    function dibujar(nodoAEnfocar) {
      enfocar = nodoAEnfocar || null;
      cuerpo.innerHTML = "";
      let rubro = 0;
      function recorrer(lista, padre, nivel, pesoPadre, numRubro) {
        const s = suma(lista) || 1;
        lista.forEach((n, i) => {
          const peso = pesoPadre * num(n.incidencia) / s;
          let numero = "";
          if (n.tipo === "rubro") numero = String(++rubro);
          else if (n.tipo === "item") numero = numRubro + "." + (i + 1);
          const tr = fila(n, lista, padre, nivel, numero, peso);
          cuerpo.appendChild(tr);
          if (n === enfocar) setTimeout(() => tr.querySelector(".te-nombre input").focus(), 0);
          if (n._plegado) {
            // Los ítems no se muestran, pero siguen contando para la numeración de los rubros.
            return;
          }
          recorrer(n.hijos || [], n, nivel + 1, peso, n.tipo === "rubro" ? numero : numRubro);
        });
      }
      recorrer(datos, null, 0, 100, "");
      if (!datos.length) {
        cuerpo.innerHTML = '<div class="lista-vacia"><i class="bi bi-list-check"></i>Todavía no hay tareas. Empezá agregando una etapa o un rubro.</div>';
      }
      const rubrosConItems = [];
      (function juntar(lista) { lista.forEach((n) => { if (n.tipo === "rubro" && n.hijos && n.hijos.length) rubrosConItems.push(n); juntar(n.hijos || []); }); })(datos);
      const todo = caja.querySelector("[data-plegar-todo]");
      if (todo) {
        const todos = rubrosConItems.length && rubrosConItems.every((n) => n._plegado);
        todo.classList.toggle("d-none", !rubrosConItems.length);
        todo.title = todos ? "Ver ítems" : "Ver solo rubros";
        todo.setAttribute("aria-label", todo.title);
        todo.querySelector("i").className = "bi " + (todos ? "bi-arrows-expand" : "bi-arrows-collapse");
      }
      const total = caja.querySelector("[data-avance-total]");
      if (total) total.textContent = fmt(datos.length ? avanceDe({ hijos: datos }) : 0) + "%";
    }

    const todo = caja.querySelector("[data-plegar-todo]");
    if (todo) todo.addEventListener("click", () => {
      const rubros = [];
      (function juntar(lista) { lista.forEach((n) => { if (n.tipo === "rubro" && n.hijos && n.hijos.length) rubros.push(n); juntar(n.hijos || []); }); })(datos);
      const plegar = !rubros.every((n) => n._plegado);
      rubros.forEach((n) => { n._plegado = plegar; });
      dibujar();
    });

    caja.querySelectorAll("[data-agregar]").forEach((b) => b.addEventListener("click", () => {
      const nuevo = { tipo: b.dataset.agregar, nombre: "", incidencia: 0, avance: 0, hijos: [] };
      datos.push(nuevo);
      fijar(datos, nuevo, 100 / datos.length);
      marcarSucio();
      dibujar(nuevo);
    }));

    form.addEventListener("submit", () => {
      campo.value = JSON.stringify(datos, (k, v) => (k === "_plegado" ? undefined : v));
      sucio = false;
    });
    window.addEventListener("beforeunload", (e) => {
      if (sucio) { e.preventDefault(); e.returnValue = ""; }
    });
    dibujar();
  }

  // --- Barras de avance (guardan solas) -----------------------------------------------------------
  function Barras(caja) {
    const url = caja.dataset.urlAvance;
    const token = caja.dataset.csrf;
    const estado = caja.querySelector("[data-estado-guardado]");
    caja.querySelectorAll("[data-barra-avance]").forEach((rango) => {
      const etiqueta = caja.querySelector('[data-avance-de="' + rango.dataset.barraAvance + '"]');
      rango.addEventListener("input", () => { if (etiqueta) etiqueta.textContent = rango.value + "%"; });
      rango.addEventListener("change", () => {
        if (estado) { estado.textContent = "Guardando…"; estado.className = "small text-muted"; }
        const cuerpo = new URLSearchParams({ avance: rango.value });
        fetch(url.replace("/0/", "/" + rango.dataset.barraAvance + "/"), {
          method: "POST", body: cuerpo, credentials: "same-origin",
          headers: { "X-CSRFToken": token, "X-Requested-With": "fetch" },
        }).then((r) => r.json().then((j) => ({ ok: r.ok, j: j }))).then(({ ok, j }) => {
          if (!ok) throw new Error(j.error || "No se pudo guardar.");
          Object.entries(j.avances).forEach(([id, av]) => {
            caja.querySelectorAll('[data-avance-calc="' + id + '"]').forEach((el) => {
              if (el.classList.contains("progress-bar")) el.style.width = av + "%";
              else el.textContent = fmt(av) + "%";
            });
          });
          document.querySelectorAll("[data-avance-obra]").forEach((el) => { el.textContent = j.avance_obra + "%"; });
          if (estado) { estado.textContent = "Guardado ✓"; estado.className = "small text-success"; }
        }).catch((err) => {
          if (estado) { estado.textContent = err.message || "No se pudo guardar. Revisá la conexión."; estado.className = "small text-danger"; }
        });
      });
    });
  }

  // --- Contraer ítems: ver solo rubros ------------------------------------------------------------
  function Plegables(lista) {
    const clave = "marta-plegados-" + (lista.dataset.clave || "");
    const caja = lista.closest(".tarjeta") || document;
    const todo = caja.querySelector("[data-plegar-todo]");
    const botones = Array.from(lista.querySelectorAll("[data-plegar]"));
    let plegados;
    try { plegados = new Set(JSON.parse(localStorage.getItem(clave) || "[]")); } catch (e) { plegados = new Set(); }

    function aplicar() {
      lista.querySelectorAll("[data-padre]").forEach((f) => f.classList.toggle("plegada", plegados.has(f.dataset.padre)));
      botones.forEach((b) => b.setAttribute("aria-expanded", plegados.has(b.dataset.plegar) ? "false" : "true"));
      if (todo) {
        const todos = botones.length && botones.every((b) => plegados.has(b.dataset.plegar));
        todo.title = todos ? "Ver ítems" : "Ver solo rubros";
        todo.setAttribute("aria-label", todo.title);
        todo.querySelector("i").className = "bi " + (todos ? "bi-arrows-expand" : "bi-arrows-collapse");
      }
      try { localStorage.setItem(clave, JSON.stringify(Array.from(plegados))); } catch (e) { /* sin almacenamiento */ }
    }
    botones.forEach((b) => b.addEventListener("click", () => {
      const id = b.dataset.plegar;
      plegados.has(id) ? plegados.delete(id) : plegados.add(id);
      aplicar();
    }));
    if (todo) {
      if (!botones.length) todo.classList.add("d-none");
      todo.addEventListener("click", () => {
        const todos = botones.every((b) => plegados.has(b.dataset.plegar));
        plegados = todos ? new Set() : new Set(botones.map((b) => b.dataset.plegar));
        aplicar();
      });
    }
    aplicar();
  }

  document.querySelectorAll("[data-editor-tareas]").forEach(Editor);
  document.querySelectorAll("[data-plegables]").forEach(Plegables);
  document.querySelectorAll("[data-barras-avance]").forEach(Barras);
})();
