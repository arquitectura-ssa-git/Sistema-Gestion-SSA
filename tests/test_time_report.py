"""Time Report: una línea para empezar, el «+» suma más y el tipo «Coordinación»."""

import re

from apps.horas.models import RegistroHoras

from .conftest import cliente_de


def test_arranca_con_una_sola_linea_y_el_boton_mas(comun):
    html = cliente_de(comun).get("/horas/").content.decode()
    assert html.count('class="fila-carga"') == 2  # la línea y el modelo para el «+»
    assert 'id="agregar-fila"' in html and "Coordinación" in html
    assert re.search(r'name="form-TOTAL_FORMS" value="1"', html)


def test_se_guardan_las_lineas_agregadas(comun, proyectos):
    datos = {"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
             "form-0-obra": proyectos[0].pk, "form-0-tipo": "produccion", "form-0-horas": "4", "form-0-extra": "on",
             "form-1-obra": proyectos[1].pk, "form-1-tipo": "coordinacion", "form-1-horas": "2.5", "form-1-extra": "on"}
    # Como extra se pueden cargar cualquier día (aunque hoy sea feriado o fin de semana).
    r = cliente_de(comun).post("/horas/", datos)
    assert r.status_code == 302
    assert sorted(RegistroHoras.objects.values_list("tipo", "horas")) == [("coordinacion", 2.5), ("produccion", 4)]


def test_coordinacion_agrega_tipos_de_tarea_y_aparecen_para_cargar(coordinador, comun):
    from apps.horas.models import TipoTarea

    c = cliente_de(coordinador)
    assert c.get("/horas/").content.decode().count('href="/horas/tipos/"') >= 1
    assert c.post("/horas/tipos/", {"nombre": "Diseño de interiores"}).status_code == 302
    nuevo = TipoTarea.objects.get(nombre="Diseño de interiores")
    assert nuevo.codigo.startswith("diseno-de")
    html = cliente_de(comun).get("/horas/").content.decode()
    assert "Diseño de interiores" in html and 'href="/horas/tipos/"' not in html
    datos = {"form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0", "form-MIN_NUM_FORMS": "0",
             "form-MAX_NUM_FORMS": "1000", "form-0-obra": "", "form-0-tipo": nuevo.codigo, "form-0-horas": "2",
             "form-0-extra": "on"}
    assert cliente_de(comun).post("/horas/", datos).status_code == 302
    assert RegistroHoras.objects.get().tipo_nombre == "Diseño de interiores"
    c.post("/horas/tipos/", {"cambiar": nuevo.pk})  # desactivado: ya no se ofrece, lo cargado queda
    from apps.horas.forms import RegistroForm

    assert nuevo.codigo not in dict(RegistroForm(usuario=comun).fields["tipo"].choices)
    assert nuevo.codigo in dict(RegistroForm(instance=RegistroHoras.objects.get(), usuario=comun).fields["tipo"].choices)
    assert cliente_de(comun).get("/horas/tipos/").status_code == 403


def test_el_tachito_esta_en_cada_linea_y_borra_la_guardada(comun):
    from apps.horas.reglas import hoy

    r = RegistroHoras.objects.create(usuario=comun, fecha=hoy(), tipo="produccion", horas=2, extra=True)
    c = cliente_de(comun)
    html = c.get("/horas/").content.decode()
    assert 'class="btn-eliminar-fila"' in html and ">Quitar<" not in html
    datos = {"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "1", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
             "form-0-id": r.pk, "form-0-tipo": "produccion", "form-0-horas": "2", "form-0-extra": "on",
             "form-0-DELETE": "on", "form-1-tipo": "produccion"}
    assert c.post("/horas/", datos).status_code == 302
    assert not RegistroHoras.objects.exists()


def test_una_linea_nueva_sin_tocar_se_ignora(comun):
    from apps.horas.reglas import hoy

    r = RegistroHoras.objects.create(usuario=comun, fecha=hoy(), tipo="gestion", horas=2, extra=True)
    datos = {"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "1", "form-MIN_NUM_FORMS": "0", "form-MAX_NUM_FORMS": "1000",
             "form-0-id": r.pk, "form-0-tipo": "gestion", "form-0-horas": "3", "form-0-extra": "on",
             "form-1-tipo": "produccion", "form-1-horas": "", "form-1-nota": ""}
    assert cliente_de(comun).post("/horas/", datos).status_code == 302
    r.refresh_from_db()
    assert r.horas == 3 and RegistroHoras.objects.count() == 1
