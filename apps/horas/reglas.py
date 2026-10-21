"""Reglas del Time Report: qué día se puede editar y cuántas horas normales entran por día."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Habilitacion

MEDIA = Decimal("0.5")


def hoy():
    return timezone.localdate()


def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def horas_contratadas(usuario, fecha):
    """Lunes a viernes: las horas del contrato. Sábado y domingo: 0 (todo es extra)."""
    return Decimal(usuario.horas_diarias or 0) if fecha.weekday() < 5 else Decimal(0)


def habilitacion_vigente(usuario, fecha):
    return Habilitacion.objects.filter(usuario=usuario, fecha=fecha, estado=Habilitacion.Estado.APROBADA,
                                       valida_hasta__gte=timezone.now()).first()


def puede_editar(usuario, fecha):
    """Hoy hasta las 23:59; un día pasado, solo con una habilitación aprobada y vigente. El futuro, nunca."""
    if fecha == hoy():
        return True
    if fecha > hoy():
        return False
    return habilitacion_vigente(usuario, fecha) is not None


def fin_del_dia():
    """23:59:59 de hoy (hora local), hasta cuando dura una habilitación aprobada."""
    return timezone.make_aware(datetime.combine(hoy(), time(23, 59, 59)))


def es_media_hora(valor):
    return valor is not None and (Decimal(valor) / MEDIA) == (Decimal(valor) / MEDIA).to_integral_value()
