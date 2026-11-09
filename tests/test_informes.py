"""Informe diario de Dirección Técnica: quién lo carga y lo lee, hasta cuándo, fotos, avance y correcciones."""

import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.horas.reglas import hoy
from apps.informes.models import FotoInforme, Gremio, HabilitacionInforme, InformeDiario
from apps.obras.models import AsignacionObra, AvanceTarea, TareaObra
from apps.plantillas import arbol

from .conftest import A, Area, asignar, cliente_de, persona


@pytest.fixture
def dt(db, obra):
    u = persona("dt@ssa.test", (A.DIRECCION_TECNICA, "integrante"))
    AsignacionObra.objects.create(obra=obra, usuario=u, area=Area.objects.get(codigo=A.DIRECCION_TECNICA))
    return u


@pytest.fixture
def coord_obras(db):
    return persona("cobras@ssa.test", (A.GESTION_OBRAS, "responsable"))


def url(obra, dia=None):
    return f"/informes/obra/{obra.pk}/{(dia or hoy()).isoformat()}/"


def foto(nombre="obra.jpg", lado=3000):
    salida = io.BytesIO()
    Image.new("RGB", (lado, lado // 2), (120, 120, 120)).save(salida, "JPEG")
    return SimpleUploadedFile(nombre, salida.getvalue(), content_type="image/jpeg")


def datos(**extra):
    albanileria = Gremio.objects.get(nombre="Albañilería")
    pintores = Gremio.objects.get(nombre="Pintores")
    return {"clima": "sol", "se_trabajo": "on", f"gremio_{albanileria.pk}": "4", f"gremio_{pintores.pk}": "2",
            "notas_pedido": "", "observaciones": "Sin novedades", **extra}


def test_el_dt_carga_el_informe_de_hoy_con_personal_y_fotos(dt, obra):
    r = cliente_de(dt).post(url(obra), datos(fotos_nuevas=[foto(), foto("b.jpg")], fotos_libro=[foto("libro.jpg")],
                                             notas_pedido="NP 12: cambiar caños"))
    assert r.status_code == 302
    inf = InformeDiario.objects.get()
    assert (inf.autor, inf.personas, inf.notas_pedido) == (dt, 6, "NP 12: cambiar caños")
    assert inf.fotos.filter(del_libro=False).count() == 2 and inf.fotos.filter(del_libro=True).count() == 1
    with Image.open(inf.fotos.first().archivo) as img:
        assert max(img.size) == 1600  # se achica sola


def test_con_sol_siempre_se_trabajo_y_con_lluvia_se_pregunta(dt, obra):
    c = cliente_de(dt)
    c.post(url(obra), datos(clima="sol", se_trabajo="", motivo_sin_trabajo="x"))
    assert InformeDiario.objects.get().se_trabajo is True
    c.post(url(obra), datos(clima="lluvia", se_trabajo="", motivo_sin_trabajo="Terreno anegado"))
    inf = InformeDiario.objects.get()
    assert (inf.clima, inf.se_trabajo, inf.motivo_sin_trabajo) == ("lluvia", False, "Terreno anegado")


def test_solo_el_dt_carga_y_lo_leen_dir_y_coordinacion_de_obras(dt, dir_, coord_obras, comun, obra):
    asignar(comun, obra, responsable=True)
    cliente_de(dt).post(url(obra), datos())
    for u in (dir_, coord_obras):
        r = cliente_de(u).get(url(obra))
        assert r.status_code == 200 and "Guardar informe" not in r.content.decode()
        assert cliente_de(u).post(url(obra), datos(observaciones="cambio")).status_code == 200
    assert InformeDiario.objects.get().observaciones == "Sin novedades"
    assert cliente_de(comun).get(url(obra)).status_code == 403
    html = cliente_de(dir_).get(f"/obras/{obra.pk}/?tab=informes").content.decode()
    assert "Informes diarios" in html and "Sin novedades" not in html and "6</td>" in html


def test_el_avance_del_informe_queda_en_el_historial(dt, obra):
    arbol.guardar(TareaObra, {"obra": obra}, [
        {"tipo": "rubro", "nombre": "Mampostería", "incidencia": Decimal(100), "avance": 0, "hijos": []}],
        con_avance=True)
    tarea = obra.tareas.get()
    cliente_de(dt).post(url(obra), datos(**{f"avance-{tarea.pk}": "40"}))
    tarea.refresh_from_db()
    obra.refresh_from_db()
    assert tarea.avance == 40 and obra.avance == 40
    assert AvanceTarea.objects.get(tarea=tarea).avance == 40
    assert "Mampostería" in cliente_de(dt).get(url(obra)).content.decode()


def test_un_dia_pasado_se_corrige_solo_con_autorizacion_de_dir(dt, dir_, obra):
    ayer = hoy() - timedelta(days=1)
    c = cliente_de(dt)
    assert c.post(url(obra, ayer), datos()).status_code == 200 and not InformeDiario.objects.exists()
    c.post(f"/informes/obra/{obra.pk}/{ayer.isoformat()}/corregir/", {"motivo": "Me olvidé"})
    pedido = HabilitacionInforme.objects.get()
    assert "Me olvidé" in cliente_de(dir_).get("/tablero/").content.decode()
    cliente_de(dir_).post(f"/informes/correcciones/{pedido.pk}/", {"accion": "aprobar"})
    assert c.post(url(obra, ayer), datos()).status_code == 302
    assert InformeDiario.objects.get().fecha == ayer
    assert c.post(url(obra, hoy() + timedelta(days=1)), datos()).status_code == 200  # el futuro, nunca
    assert InformeDiario.objects.count() == 1


def test_las_fotos_solo_las_ven_quienes_leen_el_informe(dt, comun, obra):
    cliente_de(dt).post(url(obra), datos(fotos_nuevas=[foto()]))
    f = FotoInforme.objects.get()
    assert cliente_de(dt).get(f"/informes/foto/{f.pk}/").status_code == 200
    assert cliente_de(comun).get(f"/informes/foto/{f.pk}/").status_code == 403


def test_gremios_los_editan_dt_y_coordinacion(dt, coord_obras, comun):
    assert cliente_de(dt).post("/informes/gremios/", {"nombre": "Vidrieros"}).status_code == 302
    assert Gremio.objects.filter(nombre="Vidrieros").exists()
    assert cliente_de(coord_obras).get("/informes/gremios/").status_code == 200
    assert cliente_de(comun).get("/informes/gremios/").status_code == 403


def test_el_dashboard_muestra_el_informe_pendiente(dt, obra):
    html = cliente_de(dt).get("/tablero/").content.decode()
    assert "Informe diario de hoy" in html and url(obra) in html
