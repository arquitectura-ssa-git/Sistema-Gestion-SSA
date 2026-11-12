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
    """Horas normales que se pueden cargar ese día: la jornada contratada de ese día de la semana; 0 los fines
    de semana y feriados (ahí todo lo que se cargue es extra)."""
    es_feriado = (fecha in feriados) if feriados is not None else feriado(fecha) is not None
    if es_feriado:
        return Decimal(0)
    return usuario.horas_del_dia(fecha)


def jornada_feriado(usuario, fecha, feriados=None):
    """Horas pagas que se computan solas en un feriado que cae de lunes a viernes."""
    es_feriado = (fecha in feriados) if feriados is not None else feriado(fecha) is not None
    return usuario.horas_del_dia(fecha) if es_feriado else Decimal(0)


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


def carga_horas(usuario):
    """DIR (Gerencia) no carga Time Report: ve el del equipo. Asistente de Dirección tampoco: su jornada se
    computa sola (completar_automaticos)."""
    from apps.cuentas import permisos

    return not permisos.es_gerencia(usuario) and not permisos.es_asistente_direccion(usuario)


TIPO_AUTOMATICO = "administracion"


def completar_automaticos(hasta=None):
    """Carga sola la jornada de quien es Asistente de Dirección: cada día hábil (no feriado, que ya se computa
    como jornada paga) desde que tiene el perfil, salvo los días que DIR marcó como ausencia. Se llama al abrir el
    Time Report, los reportes y el Dashboard; no duplica lo ya cargado."""
    from apps.cuentas.models import Usuario

    from .models import Ausencia, RegistroHoras

    hasta = hasta or hoy()
    nuevos = []
    for u in Usuario.objects.filter(asistente_direccion=True, is_active=True, tr_automatico_desde__isnull=False,
                                    tr_automatico_desde__lte=hasta):
        desde = u.tr_automatico_desde
        hechos = set(RegistroHoras.objects.filter(usuario=u, automatico=True, fecha__range=(desde, hasta))
                     .values_list("fecha", flat=True))
        ausente = set(Ausencia.objects.filter(usuario=u, fecha__range=(desde, hasta)).values_list("fecha", flat=True))
        feriados = feriados_en(desde, hasta)
        dia = desde
        while dia <= hasta:
            horas = u.horas_del_dia(dia)
            if horas and dia not in feriados and dia not in hechos and dia not in ausente:
                nuevos.append(RegistroHoras(usuario=u, fecha=dia, obra=None, tipo=TIPO_AUTOMATICO, horas=horas,
                                            automatico=True, nota="Jornada automática"))
            dia += timedelta(days=1)
    RegistroHoras.objects.bulk_create(nuevos)
    return len(nuevos)
