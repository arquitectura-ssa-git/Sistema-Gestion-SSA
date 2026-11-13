"""Dashboard de DIR: indicadores, lo que necesita su atención, horas por semana, avance de obras contra plazo,
últimos avances, carga del equipo, horas por tipo de tarea y próximos hitos. Todo sale de los datos que ya carga
el estudio (Time Report, tareas, informes diarios, certificados, hitos y documentos)."""

from datetime import timedelta
from decimal import Decimal

from django.db.models import Exists, OuterRef, Q, Sum
from django.urls import reverse

from apps.cuentas.models import Area, Usuario
from apps.horas import reglas
from apps.horas.models import Habilitacion, RegistroHoras, TipoTarea
from apps.obras.models import AvanceTarea, Certificado, Hito, Obra

CERO = Decimal(0)
DIAS_QUIETO = 30
SEMANAS = 8


def _personal_que_carga():
    """El personal activo que carga Time Report (DIR no carga)."""
    return (Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL, is_active=True)
            .exclude(membresias__area__codigo=Area.Codigo.GERENCIA).order_by("first_name", "last_name"))


def _compras_para_autorizar():
    from django.apps import apps as django_apps
    if not django_apps.is_installed("apps.adquisiciones"):
        return []
    from apps.adquisiciones.reglas import esperando_dir
    return list(esperando_dir()[:8])


def plazo_transcurrido(obra, hoy):
    """% del plazo que ya pasó (None si la obra no tiene fecha de inicio y fin estimada)."""
    if not (obra.fecha_inicio and obra.fecha_fin_estimada) or obra.fecha_fin_estimada <= obra.fecha_inicio:
        return None
    total = (obra.fecha_fin_estimada - obra.fecha_inicio).days
    pasado = (hoy - obra.fecha_inicio).days
    return max(0, min(100, round(pasado * 100 / total)))


def _horas_por_semana(hoy):
    lunes = reglas.lunes_de(hoy) - timedelta(weeks=SEMANAS - 1)
    filas = (RegistroHoras.objects.filter(fecha__gte=lunes, fecha__lte=hoy)
             .values("fecha", "extra").annotate(h=Sum("horas")))
    semanas = [{"lunes": lunes + timedelta(weeks=i), "normal": CERO, "extra": CERO} for i in range(SEMANAS)]
    for f in filas:
        s = semanas[(reglas.lunes_de(f["fecha"]) - lunes).days // 7]
        s["extra" if f["extra"] else "normal"] += f["h"]
    maximo = max((s["normal"] + s["extra"] for s in semanas), default=CERO) or Decimal(1)
    for s in semanas:
        s["total"] = s["normal"] + s["extra"]
        s["alto_normal"] = round(float(s["normal"] / maximo) * 170)
        s["alto_extra"] = round(float(s["extra"] / maximo) * 170)
    promedio = sum((s["total"] for s in semanas), CERO) / SEMANAS
    return semanas, promedio


def _ultimos_avances(cuantos=8):
    """Los cambios de avance más recientes. Los de un mismo certificado (o de una misma persona en la misma obra y
    día) se juntan en una línea, para que un certificado de 30 ítems no tape todo lo demás."""
    registros = (AvanceTarea.objects.filter(obra__eliminada=False)
                 .select_related("obra", "tarea", "usuario", "certificado").order_by("-creado", "-id")[:200])
    grupos = []
    for r in registros:
        clave = (r.obra_id, r.fecha, r.certificado_id or f"u{r.usuario_id}")
        if grupos and grupos[-1]["clave"] == clave:
            grupos[-1]["registros"].append(r)
            continue
        if len(grupos) == cuantos:
            break
        grupos.append({"clave": clave, "registros": [r]})
    for g in grupos:
        g["primero"] = g["registros"][0]
        g["cantidad"] = len(g["registros"])
    return grupos


def contexto(usuario):
    hoy = reglas.hoy()
    habil = hoy.weekday() < 5 and reglas.feriado(hoy) is None
    inicio_mes = hoy.replace(day=1)
    activas = Obra.objects.filter(estado=Obra.Estado.ACTIVA, eliminada=False)
    proyectos = activas.filter(tipo=Obra.Tipo.PROYECTO)
    obras = list(activas.filter(tipo=Obra.Tipo.OBRA).order_by("nombre"))

    # Proyectos quietos: activos, con tareas sin terminar y sin ningún cambio de avance en 30 días.
    hace = hoy - timedelta(days=DIAS_QUIETO)
    movidos = AvanceTarea.objects.filter(obra=OuterRef("pk"), fecha__gte=hace)
    quietos = list(activas.filter(tareas__isnull=False, avance__lt=100, creada__date__lt=hace)
                   .annotate(movido=Exists(movidos)).filter(movido=False).distinct().order_by("nombre"))

    # Obras contra plazo
    filas_obras = []
    for o in obras:
        plazo = plazo_transcurrido(o, hoy)
        dif = None if plazo is None else o.avance - plazo
        estado = ("Sin fechas" if plazo is None else f"Atrasada {-dif} pts" if dif <= -10
                  else f"Adelantada {dif} pts" if dif >= 5 else "En término")
        filas_obras.append({"obra": o, "plazo": plazo, "dif": dif, "estado": estado,
                            "atrasada": dif is not None and dif <= -10})
    atrasadas = [f for f in filas_obras if f["atrasada"]]

    # Time Report de hoy
    personal = list(_personal_que_carga())
    cargaron = set(RegistroHoras.objects.filter(fecha=hoy).values_list("usuario_id", flat=True))
    esperados = [p for p in personal if reglas.horas_contratadas(p, hoy) > 0] if habil else []
    sin_tr = [p for p in esperados if p.pk not in cargaron]

    # Informes diarios de hoy
    from apps.informes.models import HabilitacionInforme, InformeDiario

    con_informe = set(InformeDiario.objects.filter(fecha=hoy).values_list("obra_id", flat=True))
    sin_informe = [o for o in obras if o.pk not in con_informe] if habil else []

    # Horas
    mes = RegistroHoras.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy)
    horas_mes = mes.aggregate(t=Sum("horas"), e=Sum("horas", filter=Q(extra=True)))
    semanas, promedio = _horas_por_semana(hoy)
    nombres_tipo = TipoTarea.nombres()
    por_tipo = list(mes.values("tipo").annotate(h=Sum("horas")).order_by("-h"))
    total_mes = horas_mes["t"] or CERO
    maximo_tipo = por_tipo[0]["h"] if por_tipo else Decimal(1)
    tipos = [{"nombre": nombres_tipo.get(t["tipo"], t["tipo"]), "horas": t["h"],
              "pct": round(t["h"] * 100 / total_mes) if total_mes else 0,
              "ancho": round(float(t["h"] / maximo_tipo) * 100)} for t in por_tipo]

    # Carga del equipo esta semana
    lunes = reglas.lunes_de(hoy)
    semana = dict(RegistroHoras.objects.filter(fecha__gte=lunes, fecha__lte=lunes + timedelta(days=6))
                  .values_list("usuario_id").annotate(h=Sum("horas")))
    equipo = []
    for p in personal:
        jornada = p.horas_semanales
        horas = semana.get(p.pk, CERO)
        equipo.append({"persona": p, "horas": horas, "jornada": jornada,
                       "ancho": min(100, round(float(horas / jornada) * 100)) if jornada else 0,
                       "extra": jornada and horas > jornada})
    equipo.sort(key=lambda e: (-e["horas"], e["persona"].nombre_completo))

    # Certificados del mes (DIR ve montos)
    certs = Certificado.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy, obra__eliminada=False)
    cert_mes = certs.aggregate(t=Sum("periodo"))["t"]

    # Pedidos pendientes
    pedidos_horas = list(Habilitacion.objects.filter(estado=Habilitacion.Estado.PENDIENTE)
                         .select_related("usuario").order_by("pedida")[:5])
    pedidos_informe = list(HabilitacionInforme.objects.filter(estado=HabilitacionInforme.Estado.PENDIENTE)
                           .select_related("obra", "usuario").order_by("pedida")[:5])

    return {
        "dir_hoy": hoy, "dir_habil": habil,
        "kpi": {
            "proyectos": proyectos.count(), "quietos": len(quietos),
            "obras": len(obras), "atrasadas": len(atrasadas),
            "horas_mes": total_mes, "extra_mes": horas_mes["e"] or CERO,
            "tr_cargaron": len(esperados) - len(sin_tr), "tr_esperados": len(esperados),
            "informes": len(obras) - len(sin_informe) if habil else None, "obras_informe": len(obras),
            "cert_mes": cert_mes, "cert_cantidad": certs.count(),
        },
        "atencion": {
            "sin_informe": sin_informe, "sin_tr": sin_tr, "atrasadas": atrasadas, "quietos": quietos,
            "pedidos_horas": pedidos_horas, "pedidos_informe": pedidos_informe, "compras": _compras_para_autorizar(),
        },
        "semanas": semanas, "promedio_semanal": promedio,
        "obras_plazo": filas_obras,
        "ultimos_avances": _ultimos_avances(),
        "equipo_semana": equipo, "lunes_semana": lunes,
        "tipos_mes": tipos, "inicio_mes": inicio_mes,
        "proximos_hitos": (Hito.objects.filter(completado=False, fecha__gte=hoy, fecha__lte=hoy + timedelta(days=14),
                                               obra__eliminada=False).select_related("obra").order_by("fecha")[:6]),
        "url_reportes": reverse("horas:reportes"),
    }
