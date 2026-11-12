"""Clientes ↔ Agenda. Un cliente cargado en Clientes aparece solo en la Agenda (tipo Cliente), y un contacto de la
Agenda de tipo Cliente crea o actualiza su cliente. Se guarda del otro lado con una marca para no rebotar."""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.cuentas.models import Cliente


def tipo_cliente():
    from .models import TipoContacto

    tipo, _ = TipoContacto.objects.get_or_create(codigo=TipoContacto.CLIENTE, defaults={"nombre": "Clientes", "orden": 1})
    return tipo


@receiver(post_save, sender=Cliente)
def cliente_a_agenda(sender, instance, **kwargs):
    if getattr(instance, "_desde_agenda", False):
        return
    from .models import Contacto

    contacto = Contacto.objects.filter(cliente=instance).first() or Contacto(cliente=instance, tipo=tipo_cliente())
    if instance.nombres:  # una persona
        contacto.apellido, contacto.nombres = instance.apellido, instance.nombres
        if contacto.empresa == instance.apellido:
            contacto.empresa = ""
    else:  # una empresa: el contacto de referencia se carga en la Agenda
        contacto.empresa = instance.apellido
    contacto.cuit, contacto.email, contacto.telefono = instance.cuit, instance.email, instance.telefono
    contacto.domicilio, contacto.nota = instance.direccion, instance.notas
    contacto._desde_cliente = True
    contacto.save()


def contacto_a_cliente(contacto):
    """Después de guardar un contacto desde la Agenda: si es de tipo Cliente, crea o actualiza su cliente."""
    if contacto.tipo.codigo != "cliente" or getattr(contacto, "_desde_cliente", False):
        return
    cliente = contacto.cliente or Cliente()
    if contacto.empresa:
        cliente.apellido, cliente.nombres = contacto.empresa, ""
    else:
        cliente.apellido, cliente.nombres = contacto.apellido, contacto.nombres
    cliente.cuit, cliente.email, cliente.telefono = contacto.cuit, contacto.email, contacto.telefono
    cliente.direccion, cliente.notas = contacto.domicilio, contacto.nota
    cliente._desde_agenda = True
    cliente.save()
    if contacto.cliente_id != cliente.pk:
        type(contacto).objects.filter(pk=contacto.pk).update(cliente=cliente)
        contacto.cliente = cliente
