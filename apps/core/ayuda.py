"""Preguntas frecuentes de la sección Ayuda.

Para sumar o corregir una pregunta se edita esta lista: (pregunta, respuesta). La respuesta admite párrafos
separados por una línea en blanco y listas con «- » al principio de la línea.
"""

# Videos cortos (archivo en static/ayuda/, con su portada .jpg del mismo nombre).
VIDEOS = [
    {"titulo": "Cómo cargar el Time Report", "archivo": "cargar-time-report", "duracion": "30 segundos",
     "pasos": ["Menú <strong>Time Report</strong>.", "Elegí el proyecto u obra y el tipo de tarea.",
               "Escribí las horas (de a media hora).", "¿Más de un proyecto? Tocá <strong>+</strong> y sumá otra línea.",
               "Tocá <strong>Guardar horas</strong>."]},
    {"titulo": "Cómo crear un proyecto", "archivo": "crear-proyecto", "duracion": "40 segundos", "nota": "DIR y Coordinación de Proyectos",
     "pasos": ["Menú <strong>Proyectos</strong> → <strong>Nuevo proyecto</strong>.",
               "Nombre, cliente, tipo y ubicación (el código se genera solo).",
               "Etapa y estado, a la derecha.", "Elegí la plantilla de tareas y tocá <strong>Guardar</strong>.",
               "Ajustá las tareas y guardá.", "En <strong>Equipo</strong>, sumá a las personas y marcá al responsable."]},
    {"titulo": "Cómo cargar el avance y personalizar las tareas", "archivo": "avance-y-tareas", "duracion": "40 segundos",
     "nota": "Responsables, Coordinación y DIR",
     "pasos": ["Abrí el proyecto u obra → pestaña <strong>Tareas</strong>.",
               "Mové la barra de cada ítem: se guarda sola.",
               "La flecha de arriba muestra solo los rubros.",
               "Para personalizar: menú de 3 puntos → <strong>Editar tareas</strong>.",
               "Cambiá nombres e incidencias, sumá con <strong>+ Ítem</strong>, quitá con el tacho y ordená con las flechas.",
               "Tocá <strong>Guardar tareas</strong>."]},
]

SECCIONES = [
    ("Ingreso y perfil", "person-circle", [
        ("¿Cuál es la dirección del sistema?",
         "https://sophia.saezsanchez.com.ar — sirve igual en la computadora y en el celular. En el celular conviene "
         "agregarla a la pantalla de inicio para usarla como una app."),
        ("¿Con qué usuario entro?",
         "Con tu email del estudio y la contraseña que te dieron al darte de alta. La primera vez, cambiala desde "
         "Mi perfil."),
        ("Me olvidé la contraseña",
         "Pedile a DIR o a Coordinación de Proyectos que te pongan una nueva. Nadie puede ver tu contraseña: se guarda cifrada, solo se puede "
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
         "El video «Cómo cargar el Time Report» lo muestra en 30 segundos."),
        ("¿Hasta cuándo puedo cargar?",
         "El día de hoy, hasta las 23:59. Un día que ya pasó se carga solo con una habilitación: abrí ese día, "
         "escribí el motivo y tocá Pedir habilitación. Si la aprueban, tenés hasta las 23:59 del día en que la "
         "aprobaron."),
        ("¿Qué es una hora extra?",
         "Lo que pasa de tus horas contratadas de ese día. Se carga en una línea aparte con el casillero Extra "
         "marcado. Si cargás más horas normales que tu jornada, el sistema te avisa cuántas tenés que pasar a "
         "extra. Los sábados, domingos y feriados todo lo que cargues va como extra."),
        ("Falta un tipo de tarea en la lista",
         "Pedíselo a Coordinación de Proyectos o a DIR: lo agregan desde Time Report → «+ Tipo de tarea» y aparece "
         "enseguida en el Time Report de todos."),
        ("Trabajé en algo que no es de ningún proyecto",
         "Elegí «Estudio / sin proyecto» (reuniones internas, orden, capacitación…)."),
        ("Me equivoqué en una línea",
         "Si todavía es el mismo día, corregila y guardá. Para borrarla, tocá el tachito de esa línea. Si el día ya "
         "pasó, pedí habilitación."),
        ("¿Puedo repetir lo de ayer?",
         "Sí: si el día está vacío aparece el botón «Repetir lo del último día cargado». Después ajustás lo que "
         "haga falta y guardás."),
        ("En un feriado, ¿tengo que cargar algo?",
         "No. La jornada de cada persona se computa sola como paga. Si trabajaste, lo que cargues va como extra."),
    ]),
    ("Crear y cargar un proyecto", "plus-square", [
        ("¿Quién puede crear un proyecto u obra?",
         "DIR y Coordinación de Proyectos, desde Proyectos → Nuevo proyecto (u Obras → Nueva obra). Después, sus responsables y "
         "Coordinación de Proyectos pueden editarlo."),
        ("¿Qué datos son obligatorios?",
         "Solo el nombre. El código se genera solo (PR-2026-001…) si lo dejás vacío; cliente, tipo, ubicación y "
         "fechas se pueden completar después con Editar datos."),
        ("¿Plantilla o copiar otro proyecto?",
         "La plantilla trae el listado base de etapas, rubros e ítems (por ejemplo «Proyecto de Arquitectura»). "
         "Copiar otro proyecto toma sus tareas tal como quedaron ajustadas, con el avance en 0. En los dos casos "
         "se abre el editor para ajustarlas a este caso."),
        ("¿Cómo armo el equipo?",
         "En la pestaña Equipo: elegí la persona, el área por la que participa y, si corresponde, marcá "
         "«Responsable». Los responsables pueden editar los datos y las tareas. La estrella marca o desmarca al "
         "responsable y la cruz lo quita."),
        ("¿Cómo le asigno el cliente después?",
         "Menú de 3 puntos → Editar datos → Cliente. Si el cliente no existe, usá «+ Cargar un cliente nuevo» "
         "(Administración, Coordinación de Proyectos y DIR)."),
        ("¿Qué diferencia hay entre proyecto y obra?",
         "Proyecto: diseño, planos y trámites; lo ve todo el personal. Obra: construcción en ejecución; la ve su "
         "equipo (y Coordinación, Administración y DIR). Si un proyecto pasa a obra, en Editar datos cambiás "
         "«Proyecto u obra»."),
        ("¿Qué son tipo, etapa y estado?",
         "Tipo: Residencial, Comercial, Otros usos, Edificio en altura, Urbanizaciones o Masterplan. Etapa: en qué "
         "fase está (Masterplan, Anteproyecto, Proyecto ejecutivo…). Estado: Activo, Stand by (suspendido "
         "temporalmente) o Superado. Los tres sirven para filtrar la lista."),
        ("Tengo muchos proyectos para cargar",
         "Usá Proyectos → Importar desde Excel (DIR y Coordinación de Proyectos): bajá la planilla modelo, completala y subila. Se crean "
         "todos juntos con la plantilla que elijas."),
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
         "tareas. Crear y eliminar: DIR y Coordinación de Proyectos."),
        ("Borré un proyecto por error",
         "No se pierde: va a la papelera. DIR o Coordinación de Proyectos lo restauran desde Proyectos (u Obras) → Papelera."),
    ]),
    ("Tareas y avance", "list-check", [
        ("¿Cómo actualizo el avance?",
         "En la pestaña Tareas, mové la barra del ítem: se guarda sola (arriba aparece «Guardado ✓»). El avance de "
         "los rubros, las etapas y el proyecto se calcula solo; no se carga a mano."),
        ("¿Quién puede mover las barras y editar las tareas?",
         "Los responsables del proyecto u obra, Coordinación de Proyectos y DIR. El resto del equipo ve el avance "
         "pero no lo cambia."),
        ("¿Cómo personalizo las tareas de un proyecto?",
         "Menú de 3 puntos → Editar tareas. Ahí podés:\n"
         "- Cambiar el nombre de etapas, rubros e ítems.\n"
         "- Cambiar la incidencia de cada uno (el resto del grupo se reajusta para sumar 100%).\n"
         "- Sumar con «+ Rubro» o «+ Ítem».\n"
         "- Cambiar el orden con las flechas ↑ ↓.\n"
         "- Quitar con el tacho.\n\n"
         "Al final tocá Guardar tareas. Si salís sin guardar, el sistema te avisa."),
        ("¿Cambiar las tareas del proyecto cambia la plantilla?",
         "No. Las tareas se copian al crear el proyecto: lo que ajustes ahí queda solo en ese proyecto."),
        ("Si quito un ítem, ¿se pierde algo?",
         "Sí: se borra el ítem y también su historial de avance. Si la tarea ya no corresponde pero tenía avance, "
         "pensalo antes de quitarla."),
        ("¿Cómo veo solo los rubros?",
         "Con la flecha que está arriba a la derecha de la lista de tareas. La de cada rubro abre o cierra solo ese."),
        ("Armé un listado que me sirve para otros proyectos",
         "En la pestaña Tareas, panel de la derecha → Guardar como plantilla (Gestión de Proyectos, Gestión de "
         "Obras y DIR). Queda disponible al crear proyectos nuevos."),
        ("¿Qué hace «Reemplazar tareas»?",
         "Borra el listado actual del proyecto (con su historial de avance) y carga el de la plantilla elegida, con "
         "el avance en 0. Usalo solo "
         "si querés empezar de nuevo."),
        ("¿Qué son las incidencias?",
         "Cuánto pesa cada rubro o ítem dentro de su grupo. Cada grupo suma siempre 100%: si cambiás una, las "
         "demás se reajustan."),
        ("¿Cómo cargo un certificado del contratista?",
         "En la obra → Tareas → Importar certificado (Excel). El listado queda igual al del certificado y cada "
         "avance queda en el historial con la fecha. Los montos solo los ven DIR, Administración y Coordinación de Proyectos."),
        ("¿Dónde veo cuánto tardó cada tarea?",
         "Pestaña Historial de avance (DIR, Coordinación y Administración): fecha de inicio, fin y días de cada "
         "ítem."),
    ]),
    ("Informe diario de obra", "journal-richtext", [
        ("¿Quién carga el informe diario?",
         "El DT asignado a la obra (por Dirección Técnica), desde el celular o la computadora: Dashboard → «Informe "
         "diario de hoy», o en la obra → pestaña Informes diarios. Lo leen DIR y Coordinación (de Obras y de Proyectos)."),
        ("¿Qué lleva el informe?",
         "- Clima: sol o lluvia; si llovió, si se pudo trabajar.\n"
         "- Cuántas personas hubo de cada gremio.\n"
         "- El avance de las tareas: lo que muevas ahí queda también en el historial de avance de la obra.\n"
         "- Fotos de las tareas en ejecución (se achican solas).\n"
         "- Notas de pedido del libro de obra, con foto de la hoja.\n"
         "- Observaciones."),
        ("¿Hasta cuándo lo puedo cargar o corregir?",
         "El mismo día, hasta las 23:59, y lo podés guardar varias veces. Después queda cerrado: para cargarlo o "
         "corregirlo, abrí ese día y tocá «Pedir autorización»; si DIR la aprueba, tenés hasta las 23:59 de ese día."),
        ("Falta un gremio en la lista",
         "En el informe, «Editar la lista de gremios» (los DT y Coordinación de Obras). Los que desactivás dejan de "
         "aparecer en los informes nuevos."),
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


def videos():
    return VIDEOS


def secciones():
    return [{"titulo": t, "icono": i, "preguntas": [{"pregunta": p, "bloques": bloques(r)} for p, r in preguntas]}
            for t, i, preguntas in SECCIONES]
