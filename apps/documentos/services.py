"""Operaciones sobre documentos. Cada una valida, guarda y deja asentado lo que hizo."""

import string

from django.db import transaction
from django.utils import timezone

from apps.auditoria.services import registrar
from apps.cuentas import permisos

from . import formatos, procesar
from .models import Documento, VersionDocumento


class OperacionNoPermitida(Exception):
    pass


def _siguiente_revision(documento):
    ultima = documento.versiones.order_by("-numero").first()
    if ultima is None:
        return "A"
    rev = ultima.revision.upper()
    if rev.isdigit():
        return str(int(rev) + 1)
    if rev and all(c in string.ascii_uppercase for c in rev):
        # A..Z, después AA, AB…
        numero = 0
        for c in rev:
            numero = numero * 26 + (ord(c) - 64)
        numero += 1
        letras = ""
        while numero:
            numero, resto = divmod(numero - 1, 26)
            letras = chr(65 + resto) + letras
        return letras
    return str(ultima.numero + 1)


def duplicado_en_obra(obra, sha256):
    """Versión ya subida con el mismo contenido en la misma obra (o en la biblioteca general)."""
    return (VersionDocumento.objects.select_related("documento")
            .filter(sha256=sha256, documento__obra=obra, documento__en_papelera=False).first())


def _detalle_version(version):
    return {"version": version.revision, "archivo": version.nombre_original, "tamano": version.tamano,
            "sha256": version.sha256, **({"editable": version.editable_nombre} if version.editable_nombre else {})}


def _crear_version(documento, usuario, archivo, *, comentario="", revision="", editable=None, sha256=None):
    version = VersionDocumento(
        documento=documento,
        numero=(documento.versiones.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1,
        revision=(revision or _siguiente_revision(documento))[:10],
        comentario=comentario[:300],
        nombre_original=archivo.name[:255],
        tamano=archivo.size,
        sha256=sha256 or procesar.huella(archivo),
        subido_por=usuario,
    )
    version.archivo.save(archivo.name, archivo, save=False)
    if editable is not None:
        version.editable_nombre = editable.name[:255]
        version.editable_tamano = editable.size
        version.editable_sha256 = procesar.huella(editable)
        version.editable.save(editable.name, editable, save=False)
    procesar.procesar_version(version)
    if version.fecha_toma and not documento.fecha_documento:
        documento.fecha_documento = version.fecha_toma.date()
        documento.save(update_fields=["fecha_documento"])
    version.save()
    return version


@transaction.atomic
def crear_documento(usuario, archivo, *, obra, tipo, titulo="", area=None, acceso=Documento.Acceso.EQUIPO,
                    etiquetas="", comentario="", editable=None, sha256=None, **datos):
    datos_plano = procesar.leer_nombre_plano(archivo.name) if tipo == Documento.Tipo.PLANOS else {}
    documento = Documento.objects.create(
        obra=obra, tipo=tipo, area=area, acceso=acceso, etiquetas=etiquetas, creado_por=usuario,
        titulo=(titulo or datos_plano.get("titulo") or procesar.titulo_desde_nombre(archivo.name))[:200],
        numero=datos.pop("numero", "") or datos_plano.get("numero", ""),
        estado_plano=Documento.EstadoPlano.ELABORACION if tipo == Documento.Tipo.PLANOS else "",
        **datos,
    )
    version = _crear_version(documento, usuario, archivo, comentario=comentario, editable=editable, sha256=sha256,
                             revision=datos_plano.get("revision", ""))
    registrar("documento.alta", f"Subió «{documento}» ({documento.get_tipo_display()}, Rev {version.revision})",
              usuario=usuario, objeto=documento,
              detalle={**_detalle_version(version), "acceso": documento.get_acceso_display()})
    return documento, version


@transaction.atomic
def agregar_version(documento, usuario, archivo, *, comentario="", revision="", editable=None, sha256=None):
    version = _crear_version(documento, usuario, archivo, comentario=comentario, revision=revision,
                             editable=editable, sha256=sha256)
    campos = ["actualizado"]
    if documento.es_plano:
        documento.estado_plano = Documento.EstadoPlano.ELABORACION
        campos.append("estado_plano")
    documento.save(update_fields=campos)
    registrar("documento.version", f"Nueva versión de «{documento}»: Rev {version.revision}", usuario=usuario,
              objeto=documento, detalle={**_detalle_version(version), "comentario": comentario})
    return version


def enlace_repetido(obra, enlace):
    """Documento de la misma obra (o de la biblioteca) que ya usa ese enlace de Drive."""
    from .drive import analizar

    datos = analizar(enlace)
    versiones = VersionDocumento.objects.select_related("documento").filter(
        documento__obra=obra, documento__en_papelera=False).exclude(enlace="")
    for v in versiones:
        otro = v.drive
        if v.enlace == enlace or (datos and otro and otro["id"] == datos["id"]):
            return v
    return None


def _version_enlace(documento, usuario, enlace, *, comentario="", revision=""):
    from .drive import analizar

    datos = analizar(enlace) or {}
    return VersionDocumento.objects.create(
        documento=documento,
        numero=(documento.versiones.order_by("-numero").values_list("numero", flat=True).first() or 0) + 1,
        revision=(revision or _siguiente_revision(documento))[:10],
        comentario=comentario[:300], enlace=enlace,
        nombre_original=(datos.get("descripcion") or "Enlace de Drive")[:255],
        tamano=0, sha256="", subido_por=usuario,
    )


@transaction.atomic
def crear_documento_enlace(usuario, enlace, *, obra, tipo, titulo, area=None, acceso=Documento.Acceso.EQUIPO,
                           etiquetas="", comentario="", numero="", revision=""):
    documento = Documento.objects.create(
        obra=obra, tipo=tipo, area=area, acceso=acceso, etiquetas=etiquetas, creado_por=usuario,
        titulo=titulo[:200], numero=numero,
        estado_plano=Documento.EstadoPlano.ELABORACION if tipo == Documento.Tipo.PLANOS else "",
    )
    version = _version_enlace(documento, usuario, enlace, comentario=comentario, revision=revision)
    registrar("documento.alta", f"Agregó el enlace de Drive «{documento}» ({documento.get_tipo_display()}, "
              f"Rev {version.revision})", usuario=usuario, objeto=documento,
              detalle={"version": version.revision, "enlace": enlace, "acceso": documento.get_acceso_display()})
    return documento, version


@transaction.atomic
def agregar_version_enlace(documento, usuario, enlace, *, comentario="", revision=""):
    version = _version_enlace(documento, usuario, enlace, comentario=comentario, revision=revision)
    campos = ["actualizado"]
    if documento.es_plano:
        documento.estado_plano = Documento.EstadoPlano.ELABORACION
        campos.append("estado_plano")
    documento.save(update_fields=campos)
    registrar("documento.version", f"Nueva versión de «{documento}» (enlace de Drive): Rev {version.revision}",
              usuario=usuario, objeto=documento,
              detalle={"version": version.revision, "enlace": enlace, "comentario": comentario})
    return version


def subir_lote(usuario, archivos, *, obra, tipo, area, acceso, etiquetas, comentario):
    """Sube varios archivos de una vez. En planos, un DWG/RVT con el mismo nombre que un PDF va como su
    editable, y un N° de plano que ya existe en la obra entra como versión nueva de ese plano.
    Devuelve un resumen para mostrarle a la persona."""
    resumen = {"creados": [], "versiones": [], "duplicados": [], "rechazados": []}
    editables = {}
    principales = []
    for archivo in archivos:
        ext = formatos.extension(archivo.name)
        if tipo == Documento.Tipo.PLANOS and ext in formatos.EDITABLES:
            editables[archivo.name.rsplit(".", 1)[0].lower()] = archivo
        else:
            principales.append(archivo)

    for archivo in principales:
        error = formatos.validar(tipo, archivo)
        if error:
            resumen["rechazados"].append(error)
            continue
        editable = editables.pop(archivo.name.rsplit(".", 1)[0].lower(), None)
        if editable is not None:
            error = formatos.validar(tipo, editable, editable=True)
            if error:
                resumen["rechazados"].append(error)
                editable = None
        sha = procesar.huella(archivo)
        previo = duplicado_en_obra(obra, sha)
        if previo:
            resumen["duplicados"].append(f"«{archivo.name}» ya estaba subido como «{previo.documento}» "
                                         f"(Rev {previo.revision}).")
            continue
        existente = None
        if tipo == Documento.Tipo.PLANOS:
            numero = procesar.leer_nombre_plano(archivo.name).get("numero")
            if numero:
                existente = Documento.objects.filter(obra=obra, tipo=tipo, numero=numero, en_papelera=False).first()
        if existente is not None:
            if not permisos.puede_administrar_documento(usuario, existente):
                resumen["rechazados"].append(f"«{archivo.name}»: el plano {existente.numero} ya existe y no podés "
                                             "subirle versiones.")
                continue
            revision = procesar.leer_nombre_plano(archivo.name).get("revision", "")
            if revision and existente.versiones.filter(revision=revision).exists():
                revision = ""
            version = agregar_version(existente, usuario, archivo, comentario=comentario, revision=revision,
                                      editable=editable, sha256=sha)
            resumen["versiones"].append(f"{existente} → Rev {version.revision}")
        else:
            documento, _ = crear_documento(usuario, archivo, obra=obra, tipo=tipo, area=area, acceso=acceso,
                                           etiquetas=etiquetas, comentario=comentario, editable=editable, sha256=sha)
            resumen["creados"].append(documento)
    for nombre, editable in editables.items():
        resumen["rechazados"].append(f"«{editable.name}»: el editable tiene que subirse junto con el PDF del "
                                     "mismo nombre.")
    return resumen


def _guardar_cambio(documento, usuario, accion, descripcion, campos, detalle=None):
    documento.save(update_fields=campos + ["actualizado"])
    registrar(accion, descripcion, usuario=usuario, objeto=documento, detalle=detalle or {})


def cambiar_acceso(documento, usuario, acceso):
    anterior = documento.acceso
    if acceso == anterior:
        return
    if Documento.Acceso.CLIENTE in (acceso, anterior) and not permisos.puede_compartir_con_cliente(usuario, documento):
        raise OperacionNoPermitida("Solo los responsables de la obra y Gerencia comparten documentos con el cliente.")
    if acceso == Documento.Acceso.CLIENTE and not documento.obra_id:
        raise OperacionNoPermitida("Los documentos de la Biblioteca general no se comparten con clientes.")
    if acceso == Documento.Acceso.RESTRINGIDO and not documento.area_id:
        raise OperacionNoPermitida("Para restringir un documento, primero elegí su área responsable.")
    documento.acceso = acceso
    etiquetas = dict(Documento.Acceso.choices)
    accion = {"cliente": "documento.compartido"}.get(acceso, "documento.acceso")
    if anterior == Documento.Acceso.CLIENTE:
        accion = "documento.descompartido"
    _guardar_cambio(documento, usuario, accion,
                    f"«{documento}»: {etiquetas[anterior]} → {etiquetas[acceso]}", ["acceso"],
                    {"Nivel de acceso": [etiquetas[anterior], etiquetas[acceso]]})


def pasar_a_revision(documento, usuario):
    if not documento.es_plano or documento.estado_plano != Documento.EstadoPlano.ELABORACION:
        raise OperacionNoPermitida("Solo un plano en elaboración pasa a revisión.")
    documento.estado_plano = Documento.EstadoPlano.REVISION
    _guardar_cambio(documento, usuario, "plano.revision",
                    f"«{documento}» Rev {documento.version_actual.revision} pasó a revisión", ["estado_plano"])


@transaction.atomic
def aprobar_plano(documento, usuario):
    if not permisos.puede_aprobar_planos(usuario):
        raise OperacionNoPermitida("Solo Dirección Técnica y Gerencia aprueban planos para obra.")
    if not documento.es_plano or documento.estado_plano == Documento.EstadoPlano.APROBADO:
        raise OperacionNoPermitida("Ese plano ya está aprobado.")
    version = documento.version_actual
    version.aprobada_por = usuario
    version.aprobada_en = timezone.now()
    version.save(update_fields=["aprobada_por", "aprobada_en"])
    documento.estado_plano = Documento.EstadoPlano.APROBADO
    _guardar_cambio(documento, usuario, "plano.aprobado",
                    f"«{documento}» Rev {version.revision} aprobado para obra", ["estado_plano"],
                    {"version": version.revision, "sha256": version.sha256})


def observar_plano(documento, usuario, comentario):
    if not permisos.puede_aprobar_planos(usuario):
        raise OperacionNoPermitida("Solo Dirección Técnica y Gerencia revisan planos.")
    if documento.estado_plano != Documento.EstadoPlano.REVISION:
        raise OperacionNoPermitida("Solo se observa un plano que está en revisión.")
    documento.estado_plano = Documento.EstadoPlano.ELABORACION
    _guardar_cambio(documento, usuario, "plano.observado",
                    f"«{documento}» Rev {documento.version_actual.revision} volvió a elaboración con observaciones",
                    ["estado_plano"], {"observaciones": comentario})


def alternar_archivado(documento, usuario):
    documento.archivado = not documento.archivado
    _guardar_cambio(documento, usuario, "documento.archivado" if documento.archivado else "documento.desarchivado",
                    f"«{documento}» {'archivado' if documento.archivado else 'vuelve a estar vigente'}", ["archivado"])


def a_papelera(documento, usuario):
    documento.en_papelera = True
    documento.papelera_en = timezone.now()
    documento.papelera_por = usuario
    _guardar_cambio(documento, usuario, "documento.papelera", f"«{documento}» enviado a la papelera",
                    ["en_papelera", "papelera_en", "papelera_por"])


def restaurar(documento, usuario):
    documento.en_papelera = False
    documento.papelera_en = None
    documento.papelera_por = None
    _guardar_cambio(documento, usuario, "documento.restaurado", f"«{documento}» restaurado de la papelera",
                    ["en_papelera", "papelera_en", "papelera_por"])


@transaction.atomic
def eliminar_definitivo(documento, usuario):
    if not permisos.puede_eliminar_definitivo(usuario):
        raise OperacionNoPermitida("Solo Gerencia borra documentos definitivamente.")
    if not documento.en_papelera:
        raise OperacionNoPermitida("Primero mandalo a la papelera.")
    versiones = list(documento.versiones.all())
    registrar("documento.eliminado", f"Borró definitivamente «{documento}» ({len(versiones)} versiones)",
              usuario=usuario, objeto=documento, obra=documento.obra,
              detalle={"tipo": documento.get_tipo_display(), "subido_por": str(documento.creado_por or ""),
                       "versiones": [_detalle_version(v) for v in versiones]})
    archivos = []
    for v in versiones:
        archivos += [f for f in (v.archivo, v.editable, v.vista_previa) if f]
    documento.delete()
    transaction.on_commit(lambda: [f.storage.delete(f.name) for f in archivos])


def registrar_acceso(version, usuario, *, descarga, editable=False):
    documento = version.documento
    que = "el editable de " if editable else ""
    registrar("documento.descarga" if descarga else "documento.vista",
              f"{'Descargó' if descarga else 'Abrió'} {que}«{documento}» Rev {version.revision}",
              usuario=usuario, objeto=documento,
              detalle={"version": version.revision, "sha256": version.editable_sha256 if editable else version.sha256})
