"""Historial de avance de las tareas: quién cambió qué y cuándo, para ver cuánto tardó cada una de 0 a 100%."""

from datetime import date

from .models import AvanceTarea

O = AvanceTarea.Origen


def registrar(tarea, anterior, nuevo, usuario=None, fecha=None, origen=O.MANUAL, certificado=None):
    """Anota un cambio de avance. Los cambios a mano de una misma persona en un mismo día se juntan en un solo
    registro (mover la barra varias veces no llena el historial); si al final quedó igual que al empezar el día,
    el registro se borra."""
    fecha = fecha or date.today()
    if anterior == nuevo:
        return None
    if origen == O.MANUAL:
        ultimo = tarea.historial.order_by("-id").first()
        if ultimo and ultimo.fecha == fecha and ultimo.origen == O.MANUAL and ultimo.usuario_id == getattr(usuario, "pk", None):
            if ultimo.anterior == nuevo:
                ultimo.delete()
                return None
            ultimo.avance = nuevo
            ultimo.save(update_fields=["avance"])
            return ultimo
    return AvanceTarea.objects.create(tarea=tarea, obra_id=tarea.obra_id, fecha=fecha, anterior=anterior,
                                      avance=nuevo, origen=origen, certificado=certificado, usuario=usuario)


def registrar_cambios(obra, antes, usuario=None, fecha=None, origen=O.MANUAL, certificado=None):
    """Después de guardar el listado completo: anota las hojas cuyo avance cambió. `antes` es {id: avance}."""
    for tarea in obra.tareas.filter(hijos__isnull=True):
        previo = antes.get(tarea.pk, 0)
        if previo is None:
            previo = 0
        registrar(tarea, previo, tarea.avance, usuario, fecha, origen, certificado)


def retrospectiva(obra):
    """Por cada hoja con historial: cuándo empezó (pasó de 0 a algo), cuándo llegó al 100% y cuántos días tardó.

    Si la primera carga ya traía avance (por ejemplo, al importar un certificado), no se sabe cuándo empezó:
    `inicio` queda vacío y `antes_de` dice la fecha de esa primera carga.
    """
    from apps.plantillas import arbol

    nodos = arbol.anotar(obra.tareas.all())
    registros = {}
    for r in AvanceTarea.objects.filter(obra=obra).order_by("fecha", "id"):
        registros.setdefault(r.tarea_id, []).append(r)
    filas = []

    def recorrer(lista, rubro=None):
        for n in lista:
            if n.hijos_lista:
                recorrer(n.hijos_lista, n if n.tipo == "rubro" else rubro)
                continue
            historial = registros.get(n.pk, [])
            if not historial:
                continue
            inicio = fin = antes_de = None
            completa_antes = False  # ya estaba al 100% en la primera carga
            for r in historial:
                if inicio is None and antes_de is None:
                    if r.anterior is None and r.avance > 0:
                        antes_de = r.fecha
                    elif (r.anterior or 0) == 0 and r.avance > 0:
                        inicio = r.fecha
                if fin is None and not completa_antes and r.avance == 100:
                    if r.anterior is None:
                        completa_antes = True
                    elif r.anterior < 100:
                        fin = r.fecha
                if r.avance < 100:
                    fin, completa_antes = None, False  # si volvió a bajar, todavía no terminó
            dias = (fin - inicio).days if inicio and fin else None
            filas.append({"tarea": n, "rubro": rubro, "historial": historial, "inicio": inicio, "fin": fin,
                          "antes_de": antes_de, "completa_antes": completa_antes, "dias": dias})

    recorrer(nodos)
    return filas
