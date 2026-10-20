"""Carga la plantilla base «Proyecto de Arquitectura» del estudio (si todavía no existe).

Incidencias iguales dentro de cada grupo: se ajustan después desde Plantillas → Editar.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.db import migrations

NOMBRE = "Proyecto de Arquitectura"

ESTRUCTURA = [
    ("ANTEPROYECTO", [
        ("Croquis inicial / Idea", []),
        ("Planos de arquitectura", ["Planta", "Frentes", "Cortes", "Compulsa de superficies"]),
        ("Volumetría: modelo arquitectónico", []),
        ("Renders (3): frente, contrafrente y vista particular", []),
        ("Aprobación anteproyecto", [
            "Aprobación Comisión Arquitectura Country (impreso y firmado)",
            "Aprobación o visado municipal o comunal",
        ]),
    ]),
    ("PROYECTO", [
        ("Estructura", ["Planteo estructural", "Volumetría estructural-constructiva",
                        "Planos y planillas - Cálculo estructural"]),
        ("Instalación eléctrica", [
            "Planteo eléctrico int-ext / Corrientes débiles (TV, Tel, Datos, CCTV, Portero, Audio, etc.)",
            "Planos y cálculo eléctrico",
        ]),
        ("Instalación sanitaria / pluvial", [
            "Planteo sanitario y pluvial / Ventilaciones / Cámaras / Salas de máquinas / AA - CC",
            "Planos sanitarios",
        ]),
        ("Instalación de gas", ["Esquema de instalación de gas / Ventilaciones"]),
        ("Cómputos métricos", []),
        ("Memoria técnica descriptiva (s/base)", []),
        ("Planos de proyecto", ["Permiso de obra (aprobación municipal / comunal)", "Permiso de country (si aplica)"]),
    ]),
    ("PROYECTO EJECUTIVO", [
        ("Replanteo de fundaciones (ARQ + EST en 1:50)", []),
        ("Arquitectura de obra (1:50)", []),
        ("Detalles constructivos", [
            "Corte constructivo (1:25)",
            "Sector asador (si aplica / 1:25)",
            "Plano de contrapisos / Solados, solias, umbrales y bordes, narices (1:100 gral - 1:25 det.)",
            "Plano de escalera (si aplica / 1:50)",
            "Otro (especificar)",
        ]),
        ("Mobiliario fijo", ["Planos de cocina (apto cotización)", "Planos de placares y vestidor (apto cotización)"]),
        ("Diseño de baños", []),
        ("Cielorrasos e iluminación", [
            "Planteo de cielorrasos (con cortes rebatidos de detalles de gargantas, cajones, etc.)",
            "Planteo de artefactos de iluminación y planilla (si aplica)",
        ]),
        ("Carpinterías (apto cotización)", [
            "Plano de carpinterías exteriores (Alum/PVC)",
            "Plano de carpinterías interiores (madera)",
            "Plano puerta principal (diseño)",
        ]),
        ("Piscina (si aplica)", [
            "Plano de piscina / Cortes / Estructura / Iluminación",
            "Plano de solarium / Detalles y especificaciones",
            "Esquemas y planos del sistema de filtrado, bombeo y sala de máquinas",
        ]),
        ("Instalaciones especiales (AA / CC apto cotización)", [
            "Esquema de aires acondicionados",
            "Esquema de calefacción central",
        ]),
        ("Herrería", ["Planos de barandas", "Otros (especificar)"]),
    ]),
]


def partes_iguales(n):
    """n incidencias iguales que suman exactamente 100."""
    base = (Decimal(100) / n).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    return [base] * (n - 1) + [Decimal(100) - base * (n - 1)]


def cargar(apps, schema_editor):
    Plantilla = apps.get_model("plantillas", "Plantilla")
    Tarea = apps.get_model("plantillas", "TareaPlantilla")
    if Plantilla.objects.filter(nombre=NOMBRE).exists():
        return
    plantilla = Plantilla.objects.create(
        nombre=NOMBRE, uso="proyecto",
        descripcion="Anteproyecto, proyecto y proyecto ejecutivo de una obra de arquitectura.",
    )
    for i, ((etapa, rubros), inc_e) in enumerate(zip(ESTRUCTURA, partes_iguales(len(ESTRUCTURA)))):
        e = Tarea.objects.create(plantilla=plantilla, tipo="etapa", nombre=etapa, incidencia=inc_e, orden=i)
        for j, ((rubro, items), inc_r) in enumerate(zip(rubros, partes_iguales(len(rubros)))):
            r = Tarea.objects.create(plantilla=plantilla, tipo="rubro", nombre=rubro, incidencia=inc_r, orden=j, padre=e)
            for k, (item, inc_i) in enumerate(zip(items, partes_iguales(len(items)) if items else [])):
                Tarea.objects.create(plantilla=plantilla, tipo="item", nombre=item, incidencia=inc_i, orden=k, padre=r)


class Migration(migrations.Migration):
    dependencies = [("plantillas", "0002_tareas_en_arbol")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
