"""Documentos con enlace de Google Drive: no se sube el archivo, se guarda el enlace y se ve con la vista previa."""

from apps.documentos.drive import analizar
from apps.documentos.models import Documento

from .conftest import asignar, cliente_de

ARCHIVO = "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUv/view?usp=sharing"
PLANILLA = "https://docs.google.com/spreadsheets/d/1ZyXwVuTsRqPoNmLkJiHg/edit#gid=0"
CARPETA = "https://drive.google.com/drive/folders/1CarpetaDeLaObra123?usp=drive_link"


def test_reconoce_archivos_carpetas_y_documentos_de_google():
    assert analizar(ARCHIVO)["vista_previa"] == "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUv/preview"
    assert analizar(PLANILLA)["vista_previa"] == "https://docs.google.com/spreadsheets/d/1ZyXwVuTsRqPoNmLkJiHg/preview"
    assert analizar(CARPETA)["clase"] == "carpeta"
    assert analizar("https://drive.google.com/open?id=1AbCdEfGhIjKlMnOpQrStUv")["clase"] == "archivo"
    for otro in ("https://www.dropbox.com/s/abc/plano.pdf", "http://drive.google.com/file/d/1AbCdEfGhIjKl/view",
                 "cualquier cosa", ""):
        assert analizar(otro) is None


def datos(obra, **extra):
    return {"enlace": ARCHIVO, "titulo": "Planta baja", "numero": "A-101", "obra": obra.pk, "tipo": "planos",
            "acceso": "equipo", **extra}


def test_agregar_un_enlace_crea_el_documento_sin_subir_nada(comun, obra):
    asignar(comun, obra)
    respuesta = cliente_de(comun).post("/documentos/enlace/", datos(obra))
    doc = Documento.objects.get()
    assert respuesta.status_code == 302 and respuesta["Location"].endswith(f"/documentos/{doc.pk}/")
    v = doc.version_actual
    assert (doc.titulo, doc.numero, v.revision, v.enlace, v.archivo.name) == ("Planta baja", "A-101", "A", ARCHIVO, "")
    html = cliente_de(comun).get(f"/documentos/{doc.pk}/").content.decode()
    assert "https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUv/preview" in html
    # Abrir y «descargar» llevan a Drive.
    for url in (f"/documentos/archivo/{v.pk}/ver/", f"/documentos/archivo/{v.pk}/descargar/"):
        r = cliente_de(comun).get(url)
        assert r.status_code == 302 and r["Location"] == ARCHIVO


def test_se_rechazan_los_enlaces_que_no_son_de_drive(comun, obra):
    asignar(comun, obra)
    r = cliente_de(comun).post("/documentos/enlace/", datos(obra, enlace="https://www.dropbox.com/s/abc/plano.pdf"))
    assert r.status_code == 200 and "Tiene que ser un enlace de Google Drive" in r.content.decode()
    assert not Documento.objects.exists()


def test_el_mismo_enlace_no_se_carga_dos_veces(comun, obra):
    asignar(comun, obra)
    c = cliente_de(comun)
    c.post("/documentos/enlace/", datos(obra))
    c.post("/documentos/enlace/", datos(obra, titulo="Otra vez", enlace=ARCHIVO.replace("view", "edit")))
    assert Documento.objects.count() == 1


def test_una_version_nueva_puede_ser_un_enlace(comun, obra):
    asignar(comun, obra)
    c = cliente_de(comun)
    c.post("/documentos/enlace/", datos(obra))
    doc = Documento.objects.get()
    otro = "https://drive.google.com/file/d/1RevisionBdelPlano0000/view"
    c.post(f"/documentos/{doc.pk}/version/", {"enlace": otro, "comentario": "Se movió el tabique"})
    assert [(v.revision, v.enlace) for v in doc.versiones.order_by("numero")] == [("A", ARCHIVO), ("B", otro)]


def test_solo_lo_ve_quien_puede_ver_el_documento(comun, otro, obra):
    asignar(comun, obra)
    cliente_de(comun).post("/documentos/enlace/", datos(obra))
    doc = Documento.objects.get()
    assert cliente_de(otro).get(f"/documentos/{doc.pk}/").status_code == 403
    assert cliente_de(otro).get(f"/documentos/archivo/{doc.version_actual.pk}/ver/").status_code == 403
