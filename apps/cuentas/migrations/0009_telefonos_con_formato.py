from django.db import migrations, models

from apps.core.telefono import normalizar


def adelante(apps, schema_editor):
    for nombre in ("Usuario", "Cliente"):
        modelo = apps.get_model("cuentas", nombre)
        for obj in modelo.objects.exclude(telefono=""):
            nuevo = normalizar(obj.telefono)
            if nuevo != obj.telefono:
                modelo.objects.filter(pk=obj.pk).update(telefono=nuevo)


class Migration(migrations.Migration):
    dependencies = [("cuentas", "0008_domicilio_del_personal")]
    operations = [
        migrations.AlterField("usuario", "telefono", models.CharField(
            "WhatsApp", max_length=30, blank=True, help_text="País, característica y número, ej: +54 381 300-4288")),
        migrations.RunPython(adelante, migrations.RunPython.noop),
    ]
