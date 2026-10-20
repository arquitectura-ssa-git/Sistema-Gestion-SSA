"""Plantillas de ejemplo para `manage.py cargar_demo`."""

from decimal import Decimal

from .models import Plantilla, TareaPlantilla

PLANTILLAS = [
    ("Vivienda unifamiliar", Plantilla.Uso.OBRA, "Rubros típicos de una casa de 1 o 2 plantas.", [
        ("Trabajos preliminares y obrador", 3), ("Movimiento de suelos y excavación", 4),
        ("Fundaciones", 8), ("Estructura de hormigón", 17), ("Mampostería", 10),
        ("Cubierta", 7), ("Instalación sanitaria", 7), ("Instalación eléctrica", 6),
        ("Instalación de gas", 3), ("Revoques y contrapisos", 8), ("Pisos y revestimientos", 8),
        ("Carpinterías", 7), ("Pintura", 4), ("Terminaciones y limpieza final", 8),
    ]),
    ("Proyecto ejecutivo", Plantilla.Uso.PROYECTO, "Etapas de diseño hasta la documentación para obra.", [
        ("Relevamiento y programa de necesidades", 5), ("Anteproyecto", 20), ("Proyecto básico", 20),
        ("Documentación ejecutiva", 30), ("Cómputo y presupuesto", 10), ("Trámites municipales", 15),
    ]),
]


def cargar_plantillas_demo(usuario=None):
    creadas = {}
    for nombre, uso, descripcion, tareas in PLANTILLAS:
        plantilla, nueva = Plantilla.objects.get_or_create(
            nombre=nombre, defaults={"uso": uso, "descripcion": descripcion, "creada_por": usuario})
        if nueva:
            TareaPlantilla.objects.bulk_create([
                TareaPlantilla(plantilla=plantilla, nombre=t, incidencia=Decimal(i), orden=n)
                for n, (t, i) in enumerate(tareas)
            ])
        creadas[nombre] = plantilla
    return creadas
