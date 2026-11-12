"""Tipos con los que arranca la Agenda y un contacto por cada cliente que ya existe."""

from django.db import migrations


def cargar(apps, schema_editor):
    TipoContacto = apps.get_model("agenda", "TipoContacto")
    Contacto = apps.get_model("agenda", "Contacto")
    Cliente = apps.get_model("cuentas", "Cliente")
    proveedor, _ = TipoContacto.objects.get_or_create(codigo="proveedor", defaults={"nombre": "Proveedores", "orden": 0})
    cliente_t, _ = TipoContacto.objects.get_or_create(codigo="cliente", defaults={"nombre": "Clientes", "orden": 1})
    for c in Cliente.objects.all():
        if Contacto.objects.filter(cliente=c).exists():
            continue
        persona = bool(c.nombres)
        Contacto.objects.create(
            tipo=cliente_t, cliente=c, empresa="" if persona else c.apellido,
            apellido=c.apellido if persona else "", nombres=c.nombres if persona else "",
            cuit=c.cuit, email=c.email, telefono=c.telefono, domicilio=c.direccion, nota=c.notas)


class Migration(migrations.Migration):

    dependencies = [("agenda", "0001_inicial"), ("cuentas", "0007_asistente_de_direccion")]

    operations = [migrations.RunPython(cargar, migrations.RunPython.noop)]
