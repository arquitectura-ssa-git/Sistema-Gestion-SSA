from django.db import migrations, models


def copiar_jornada(apps, schema_editor):
    Usuario = apps.get_model("cuentas", "Usuario")
    for u in Usuario.objects.all():
        for dia in ("lun", "mar", "mie", "jue", "vie"):
            setattr(u, f"horas_{dia}", u.horas_diarias)
        u.save(update_fields=[f"horas_{d}" for d in ("lun", "mar", "mie", "jue", "vie")])


def campo(nombre):
    return models.DecimalField(nombre, max_digits=3, decimal_places=1, default=8)


class Migration(migrations.Migration):

    dependencies = [
        ("cuentas", "0003_horas_diarias"),
    ]

    operations = [
        migrations.AddField(model_name="usuario", name="horas_lun", field=campo("lunes")),
        migrations.AddField(model_name="usuario", name="horas_mar", field=campo("martes")),
        migrations.AddField(model_name="usuario", name="horas_mie", field=campo("miércoles")),
        migrations.AddField(model_name="usuario", name="horas_jue", field=campo("jueves")),
        migrations.AddField(model_name="usuario", name="horas_vie", field=campo("viernes")),
        migrations.RunPython(copiar_jornada, migrations.RunPython.noop),
        migrations.RemoveField(model_name="usuario", name="horas_diarias"),
    ]
