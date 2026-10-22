"""Foto de perfil."""

from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from PIL import Image

from .conftest import cliente_de


def foto(ancho=800, alto=600, formato="PNG"):
    salida = BytesIO()
    Image.new("RGB", (ancho, alto), (120, 120, 120)).save(salida, formato)
    return SimpleUploadedFile(f"yo.{formato.lower()}", salida.getvalue())


def perfil(usuario, **extra):
    return {"first_name": usuario.first_name, "last_name": "Prueba", "cargo": "", "telefono": "",
            "notif_email": "on", **extra}


def test_subir_la_foto_la_recorta_cuadrada_y_chica(comun):
    r = cliente_de(comun).post("/personal/mi-perfil/", {**perfil(comun), "foto_nueva": foto()})
    assert r.status_code == 302
    comun.refresh_from_db()
    with Image.open(comun.foto.open("rb")) as imagen:
        assert imagen.size == (256, 256) and imagen.format == "JPEG"
    html = cliente_de(comun).get("/tablero/").content.decode()
    assert f"/personal/{comun.pk}/foto/" in html  # arriba a la derecha


def test_un_archivo_que_no_es_imagen_se_rechaza(comun):
    r = cliente_de(comun).post("/personal/mi-perfil/",
                               {**perfil(comun), "foto_nueva": SimpleUploadedFile("yo.jpg", b"no soy una foto")})
    assert r.status_code == 200 and "No se pudo leer la imagen" in r.content.decode()
    comun.refresh_from_db()
    assert not comun.foto


def test_quitar_la_foto(comun):
    c = cliente_de(comun)
    c.post("/personal/mi-perfil/", {**perfil(comun), "foto_nueva": foto()})
    c.post("/personal/mi-perfil/", {**perfil(comun), "quitar_foto": "on"})
    comun.refresh_from_db()
    assert not comun.foto


def test_la_foto_la_ve_el_personal_pero_no_alguien_sin_sesion(comun, otro):
    cliente_de(comun).post("/personal/mi-perfil/", {**perfil(comun), "foto_nueva": foto()})
    assert cliente_de(otro).get(f"/personal/{comun.pk}/foto/").status_code == 200
    assert Client().get(f"/personal/{comun.pk}/foto/").status_code == 302  # al login
