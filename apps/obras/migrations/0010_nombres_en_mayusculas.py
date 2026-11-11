"""Los nombres de proyectos y obras pasan a mayúsculas (desde ahora se guardan siempre así)."""

from django.db import migrations


def a_mayusculas(apps, schema_editor):
    Obra = apps.get_model("obras", "Obra")
    for o in Obra.objects.all():
        nombre = " ".join(o.nombre.split()).upper()
        if nombre != o.nombre:
            Obra.objects.filter(pk=o.pk).update(nombre=nombre)


class Migration(migrations.Migration):

    dependencies = [("obras", "0009_tipo_de_uso")]

    operations = [migrations.RunPython(a_mayusculas, migrations.RunPython.noop)]
