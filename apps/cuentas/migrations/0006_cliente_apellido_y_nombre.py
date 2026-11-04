"""Clientes: «Apellido o razón social» (en mayúsculas) y «Nombre» por separado.

Los clientes que ya estaban pasan su nombre completo al apellido, en mayúsculas; después se pueden separar
editándolos.
"""

from django.db import migrations, models


def pasar_nombre_al_apellido(apps, schema_editor):
    Cliente = apps.get_model("cuentas", "Cliente")
    for c in Cliente.objects.all():
        c.apellido = " ".join(c.nombre.split()).upper()
        c.nombre = c.apellido
        c.save(update_fields=["apellido", "nombre"])


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0005_foto_de_perfil"),
    ]

    operations = [
        migrations.AddField(
            model_name="cliente",
            name="apellido",
            field=models.CharField(default="", help_text="Se guarda siempre en mayúsculas.", max_length=150,
                                   verbose_name="apellido o razón social"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="cliente",
            name="nombres",
            field=models.CharField(blank=True, help_text="Solo para personas. Vacío si es una empresa.",
                                   max_length=100, verbose_name="nombre"),
        ),
        migrations.AlterField(
            model_name="cliente",
            name="nombre",
            field=models.CharField(editable=False, max_length=260),
        ),
        migrations.RunPython(pasar_nombre_al_apellido, migrations.RunPython.noop),
    ]
