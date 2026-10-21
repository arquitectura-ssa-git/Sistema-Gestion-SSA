"""24/12 y 31/12/2026: el estudio no trabaja."""

from datetime import date

from django.db import migrations

DIAS = [
    (date(2026, 12, 24), "Nochebuena (el estudio no trabaja)"),
    (date(2026, 12, 31), "Fin de año (el estudio no trabaja)"),
]


def cargar(apps, schema_editor):
    Feriado = apps.get_model("horas", "Feriado")
    for fecha, nombre in DIAS:
        Feriado.objects.update_or_create(fecha=fecha, defaults={"nombre": nombre, "tipo": "no_laborable", "aplica": True})


class Migration(migrations.Migration):
    dependencies = [("horas", "0003_feriados_2026")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
