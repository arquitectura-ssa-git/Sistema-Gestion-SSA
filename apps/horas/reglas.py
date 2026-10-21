"""Reglas del Time Report: qué día se puede editar y cuántas horas normales entran por día."""

from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from .models import Feriado, Habilitacion

MEDIA = Decimal("0.5")


def hoy():
    return timezone.localdate()


def lunes_de(fecha):
    return fecha - timedelta(days=fecha.weekday())


def feriado(fecha):
    """El feriado que aplica al estudio ese día, o None."""
    return Feriado.objects.filter(fecha=fecha, aplica=True).first()


def feriados_en(desde, hasta):
    return {f.fecha: f for f in Feriado.objects.filter(fecha__range=(desde, hasta), aplica=True)}


def horas_contratadas(usuario, fecha, feriados=None):
    """Horas normales que se pueden cargar ese día: la jornada de lunes a viernes; 0 los fines de semana
    y feriados (ahí todo lo que se cargue es extra)."""
    es_feriado = (fecha in feriados) if feriados is not None else feriado(fecha) is not None
    if fecha.weekday() >= 5 or es_feriado:
        return Decimal(0)
    return Decimal(usuario.horas_diarias or 0)


def jornada_feriado(usuario, fecha, feriados=None):
    """Horas pagas que se computan solas en un feriado que cae de lunes a viernes."""
    es_feriado = (fecha in feriados) if feriados is not None else feriado(fecha) is not None
    if es_feriado and fecha.weekday() < 5:
        return Decimal(usuario.horas_diarias or 0)
    return Decimal(0)


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
