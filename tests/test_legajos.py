"""Legajos: solo DIR y Asistente de Dirección los ven y gestionan; los archivos se sirven con permiso."""

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.auditoria.models import RegistroActividad
from apps.horas import reglas
from apps.legajos.models import DocumentoLegajo

from .conftest import A, cliente_de, persona


@pytest.fixture
def asistente(db):
    u = persona("asis@ssa.test", (A.GESTION_ADMINISTRATIVA, "integrante"))
    u.asistente_direccion = True
    u.save()
    return u


def pdf(nombre="dni.pdf"):
    return SimpleUploadedFile(nombre, b"%PDF-1.4 prueba", content_type="application/pdf")


def test_solo_dir_y_asistente_entran(dir_, asistente, coordinador, administracion, comun):
    for u in (dir_, asistente):
        assert cliente_de(u).get("/personal/legajos/").status_code == 200
        assert 'href="/personal/legajos/"' in cliente_de(u).get("/personal/").content.decode()
    for u in (coordinador, administracion, comun):
        assert cliente_de(u).get("/personal/legajos/").status_code == 403
        assert cliente_de(u).get(f"/personal/legajos/{comun.pk}/").status_code == 403
        assert 'href="/personal/legajos/"' not in cliente_de(u).get("/personal/").content.decode()


def test_subir_ver_y_quitar_un_documento(asistente, comun):
    c = cliente_de(asistente)
    vence = reglas.hoy() + timedelta(days=30)
    r = c.post(f"/personal/legajos/{comun.pk}/", {"tipo": "contrato", "archivo": pdf("convenio.pdf"),
                                                  "vence": vence.isoformat()})
    assert r.status_code == 302
    doc = DocumentoLegajo.objects.get()
    assert (doc.usuario, doc.tipo, doc.vence, doc.nombre_original) == (comun, "contrato", vence, "convenio.pdf")
    assert c.get(f"/personal/legajos/documento/{doc.pk}/").status_code == 200
    assert cliente_de(comun).get(f"/personal/legajos/documento/{doc.pk}/").status_code == 403
    html = c.get("/personal/legajos/").content.decode()
    assert "Faltan 3" in html and "vence" in html
    c.post(f"/personal/legajos/documento/{doc.pk}/quitar/")
    assert not DocumentoLegajo.objects.exists()
    acciones = set(RegistroActividad.objects.values_list("accion", flat=True))
    assert {"legajo.alta", "legajo.ver", "legajo.baja"} <= acciones


def test_solo_pdf_o_fotos_y_otros_con_nombre(dir_, comun):
    c = cliente_de(dir_)
    c.post(f"/personal/legajos/{comun.pk}/", {"tipo": "dni", "archivo": SimpleUploadedFile("x.exe", b"MZ")})
    c.post(f"/personal/legajos/{comun.pk}/", {"tipo": "otro", "archivo": pdf("cv.pdf")})
    assert not DocumentoLegajo.objects.exists()
    c.post(f"/personal/legajos/{comun.pk}/", {"tipo": "otro", "nombre": "CV", "archivo": pdf("cv.pdf")})
    assert DocumentoLegajo.objects.get().titulo == "CV"
