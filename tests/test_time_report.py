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
             "form-0-obra": proyectos[0].pk, "form-0-tipo": "produccion", "form-0-horas": "4",
             "form-1-obra": proyectos[1].pk, "form-1-tipo": "coordinacion", "form-1-horas": "2.5"}
    r = cliente_de(comun).post("/horas/", datos)
    assert r.status_code == 302
    assert sorted(RegistroHoras.objects.values_list("tipo", "horas")) == [("coordinacion", 2.5), ("produccion", 4)]
