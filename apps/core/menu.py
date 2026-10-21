"""Menú lateral. Cada ítem: (nombre de url, texto, ícono bootstrap, permiso requerido).

Los ítems cuyo url todavía no existe se omiten solos, así el menú crece a
medida que se agregan secciones.
"""

from django.urls import NoReverseMatch, reverse

MENU_PERSONAL = [
    ("", [
        ("core:tablero", "Dashboard", "speedometer2", None),
        ("proyectos:lista", "Proyectos", "pencil-square", None),
        ("obras:lista", "Obras", "buildings", None),
        ("documentos:lista", "Documentos", "folder2-open", None),
        ("cuentas:personal", "Equipo", "people", None),
        ("cuentas:clientes", "Clientes", "person-vcard", "clientes"),
        ("plantillas:lista", "Plantillas", "list-check", None),
        ("horas:mio", "Time Report", "clock", None),
    ]),
]

MENU_CLIENTE = [
    ("portal:inicio", "Mis obras", "house", None),
    ("portal:solicitudes", "Aprobaciones", "check2-square", None),
    ("comunicados:recibidos", "Mensajes", "envelope", None),
    ("notificaciones:lista", "Notificaciones", "bell", None),
]


def _item(request, nombre_url, texto, icono):
    try:
        url = reverse(nombre_url)
    except NoReverseMatch:
        return None
    return {"url": url, "texto": texto, "icono": icono, "activo": False, "nombre_url": nombre_url}


def _marcar_activo(request, items):
    """Ilumina un solo ítem: el que la vista indicó, o el de url más larga que coincide con la página."""
    marcado = getattr(request, "menu_activo", None)
    if marcado:
        candidatos = [x for x in items if x["nombre_url"] == marcado]
    else:
        candidatos = [x for x in items
                      if (request.path == x["url"] if x["url"] == "/" else request.path.startswith(x["url"]))]
    if candidatos:
        max(candidatos, key=lambda x: len(x["url"]))["activo"] = True


def construir_menu(request, perm):
    if perm.get("cliente"):
        items = [x for x in (_item(request, u, t, i) for u, t, i, _ in MENU_CLIENTE) if x]
        _marcar_activo(request, items)
        return [{"titulo": "", "items": items}]
    menu = []
    for titulo, entradas in MENU_PERSONAL:
        items = [
            _item(request, u, t, i) for u, t, i, requiere in entradas
            if requiere is None or perm.get(requiere)
        ]
        items = [x for x in items if x]
        if items:
            menu.append({"titulo": titulo, "items": items})
    _marcar_activo(request, [x for grupo in menu for x in grupo["items"]])
    return menu
