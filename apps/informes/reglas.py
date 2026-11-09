"""Cuándo se puede cargar o corregir un informe diario (igual que el Time Report: el día, hasta las 23:59; un día
pasado, solo con una habilitación de DIR aprobada y vigente)."""

from django.utils import timezone

from apps.horas.reglas import feriado, hoy

from .models import HabilitacionInforme

MAX_FOTOS = 20


def habilitacion_vigente(obra, fecha):
    return HabilitacionInforme.objects.filter(obra=obra, fecha=fecha, estado=HabilitacionInforme.Estado.APROBADA,
                                              valida_hasta__gte=timezone.now()).first()


def abierto(obra, fecha):
    if fecha == hoy():
        return True
    if fecha > hoy():
        return False
    return habilitacion_vigente(obra, fecha) is not None


def es_dia_habil(fecha):
    return fecha.weekday() < 5 and feriado(fecha) is None
