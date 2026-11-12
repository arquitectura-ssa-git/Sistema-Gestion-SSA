from django.db import migrations

from apps.core.telefono import normalizar


def adelante(apps, schema_editor):
    Contacto = apps.get_model("agenda", "Contacto")
    for c in Contacto.objects.exclude(telefono=""):
        nuevo = normalizar(c.telefono)
        if nuevo != c.telefono:
            Contacto.objects.filter(pk=c.pk).update(telefono=nuevo)


class Migration(migrations.Migration):
    dependencies = [("agenda", "0002_tipos_y_clientes"), ("cuentas", "0009_telefonos_con_formato")]
    operations = [migrations.RunPython(adelante, migrations.RunPython.noop)]
