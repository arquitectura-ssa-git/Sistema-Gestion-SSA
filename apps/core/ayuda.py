"""Preguntas frecuentes de la sección Ayuda.

Para sumar o corregir una pregunta se edita esta lista: (pregunta, respuesta). La respuesta admite párrafos
separados por una línea en blanco y listas con «- » al principio de la línea.
"""

SECCIONES = [
    ("Ingreso y perfil", "person-circle", [
        ("¿Cuál es la dirección del sistema?",
         "https://sophia.saezsanchez.com.ar — sirve igual en la computadora y en el celular. En el celular conviene "
         "agregarla a la pantalla de inicio para usarla como una app."),
        ("¿Con qué usuario entro?",
         "Con tu email del estudio y la contraseña que te dio Gerencia (DIR). La primera vez, cambiala desde "
         "Mi perfil."),
        ("Me olvidé la contraseña",
         "Pedile a DIR que te ponga una nueva. Nadie puede ver tu contraseña: se guarda cifrada, solo se puede "
         "cambiar."),
        ("¿Cómo cambio mi contraseña o mi foto?",
         "Arriba a la derecha, tocá tu nombre → Mi perfil. Ahí cambiás la foto (se recorta sola), tu WhatsApp y "
         "por dónde querés recibir los avisos."),
    ]),
    ("Time Report", "clock", [
        ("¿Cómo cargo mis horas?",
         "Menú Time Report. En la línea de hoy:\n"
         "- Elegí el proyecto u obra (arriba aparecen los tuyos).\n"
         "- Elegí el tipo de tarea: Producción, Gestión, Coordinación, Administración, Compras o Capacitación.\n"
         "- Escribí las horas (de a media hora: 1, 1,5, 2…).\n"
         "- Si trabajaste en más de un proyecto, tocá el «+» para sumar otra línea.\n"
         "- Tocá Guardar horas.\n\n"
         "El video de esta página lo muestra en 30 segundos."),
        ("¿Hasta cuándo puedo cargar?",
         "El día de hoy, hasta las 23:59. Un día que ya pasó se carga solo con una habilitación: abrí ese día, "
         "escribí el motivo y tocá Pedir habilitación. Si la aprueban, tenés hasta las 23:59 del día en que la "
         "aprobaron."),
        ("¿Qué es una hora extra?",
         "Lo que pasa de tus horas contratadas de ese día. Se carga en una línea aparte con el casillero Extra "
         "marcado. Si cargás más horas normales que tu jornada, el sistema te avisa cuántas tenés que pasar a "
         "extra. Los sábados, domingos y feriados todo lo que cargues va como extra."),
        ("Trabajé en algo que no es de ningún proyecto",
         "Elegí «Estudio / sin proyecto» (reuniones internas, orden, capacitación…)."),
        ("Me equivoqué en una línea",
         "Si todavía es el mismo día, corregila y guardá. Para borrarla, marcá Quitar y guardá. Si el día ya "
         "pasó, pedí habilitación."),
        ("¿Puedo repetir lo de ayer?",
         "Sí: si el día está vacío aparece el botón «Repetir lo del último día cargado». Después ajustás lo que "
         "haga falta y guardás."),
        ("En un feriado, ¿tengo que cargar algo?",
         "No. La jornada de cada persona se computa sola como paga. Si trabajaste, lo que cargues va como extra."),
    ]),
    ("Proyectos y obras", "pencil-square", [
        ("¿Qué proyectos y obras veo?",
         "Todos los proyectos. De las obras, las de tu equipo (Coordinación, Administración y DIR ven todas). "
         "Los tuyos aparecen primero, en negrita y con un punto."),
        ("¿Cómo busco o filtro?",
         "Arriba de la lista: buscar por nombre, código, cliente o localidad, y filtrar por Tipo (Residencial, "
         "Comercial…), Estado (Activo, Stand by, Superado) y Etapa."),
        ("¿Quién puede editar un proyecto?",
         "Sus responsables, Coordinación de Proyectos y DIR, desde el menú de 3 puntos → Editar datos o Editar "
         "tareas. Crear y eliminar es solo de DIR."),
        ("¿Cómo creo varios proyectos de una vez?",
         "Solo DIR: Proyectos → Importar desde Excel. Bajá la planilla modelo, completala y subila. Antes de "
         "crear nada te muestra qué va a pasar con cada fila."),
        ("Borré un proyecto por error",
         "No se pierde: va a la papelera. DIR lo restaura desde Proyectos (u Obras) → Papelera."),
    ]),
    ("Tareas y avance", "list-check", [
        ("¿Cómo actualizo el avance?",
         "En la pestaña Tareas, mové la barra del ítem: se guarda sola. El avance de los rubros, las etapas y el "
         "proyecto se calcula solo."),
        ("¿Qué son las incidencias?",
         "Cuánto pesa cada rubro o ítem dentro de su grupo. Cada grupo suma siempre 100%: si cambiás una, las "
         "demás se reajustan."),
        ("¿Cómo cargo un certificado del contratista?",
         "En la obra → Tareas → Importar certificado (Excel). El listado queda igual al del certificado y cada "
         "avance queda en el historial con la fecha. Los montos solo los ven DIR y Administración."),
        ("¿Dónde veo cuánto tardó cada tarea?",
         "Pestaña Historial de avance (DIR, Coordinación y Administración): fecha de inicio, fin y días de cada "
         "ítem."),
    ]),
    ("Documentos", "folder2-open", [
        ("¿Cómo subo un archivo?",
         "En el proyecto u obra → Archivos, o en Documentos → Subir archivos. Si el archivo ya está en Google Drive, usá "
         "«Enlace de Drive»: no se duplica y se ve con vista previa."),
        ("¿Por qué no puedo abrir un enlace de Drive?",
         "Quién puede abrirlo lo decide Drive: pedile a quien lo subió que lo comparta con tu cuenta (o con el "
         "estudio)."),
        ("Borré un documento",
         "Va a la papelera de Documentos. Solo DIR lo puede borrar definitivamente."),
    ]),
]


def bloques(texto):
    """Separa la respuesta en párrafos y listas para la plantilla."""
    resultado = []
    for parrafo in texto.split("\n\n"):
        lineas = [x.strip() for x in parrafo.split("\n") if x.strip()]
        items = [x[2:] for x in lineas if x.startswith("- ")]
        texto_suelto = " ".join(x for x in lineas if not x.startswith("- "))
        if texto_suelto:
            resultado.append({"tipo": "p", "texto": texto_suelto})
        if items:
            resultado.append({"tipo": "lista", "items": items})
    return resultado


def secciones():
    return [{"titulo": t, "icono": i, "preguntas": [{"pregunta": p, "bloques": bloques(r)} for p, r in preguntas]}
            for t, i, preguntas in SECCIONES]
