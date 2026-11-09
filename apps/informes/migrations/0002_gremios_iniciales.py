"""Gremios con los que arranca la lista (los DT y Coordinación de Obras la pueden cambiar)."""

from django.db import migrations

GREMIOS = ["Albañilería", "Electricistas", "Plomeros", "Gasistas", "Pintores", "Herreros", "Carpinteros",
           "Durlock / Yeseros", "Techistas", "Ayudantes", "Otros"]


def cargar(apps, schema_editor):
    Gremio = apps.get_model("informes", "Gremio")
    for i, nombre in enumerate(GREMIOS):
        Gremio.objects.get_or_create(nombre=nombre, defaults={"orden": i})


class Migration(migrations.Migration):

    dependencies = [("informes", "0001_inicial")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
