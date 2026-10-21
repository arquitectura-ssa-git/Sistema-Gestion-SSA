"""Feriados de lo que queda de 2026. Los locales de otras provincias quedan cargados pero sin aplicar
(el estudio está en Tucumán); se cambian desde Time Report → Feriados."""

from datetime import date

from django.db import migrations

FERIADOS = [
    (date(2026, 11, 9), "Feriado nacional extraordinario (visita del papa León XIV)", "nacional", True),
    (date(2026, 11, 10), "Feriado local CABA y Córdoba (visita del Papa)", "local", False),
    (date(2026, 11, 11), "Feriado local Provincia de Buenos Aires (visita del Papa)", "local", False),
    (date(2026, 11, 23), "Día de la Soberanía Nacional (trasladado del 20/11)", "nacional", True),
    (date(2026, 12, 7), "Día no laborable con fines turísticos", "no_laborable", True),
    (date(2026, 12, 8), "Inmaculada Concepción de María", "nacional", True),
    (date(2026, 12, 25), "Navidad", "nacional", True),
]


def cargar(apps, schema_editor):
    Feriado = apps.get_model("horas", "Feriado")
    for fecha, nombre, tipo, aplica in FERIADOS:
        Feriado.objects.get_or_create(fecha=fecha, defaults={"nombre": nombre, "tipo": tipo, "aplica": aplica})


class Migration(migrations.Migration):
    dependencies = [("horas", "0002_feriado")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
