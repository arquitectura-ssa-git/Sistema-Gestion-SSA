"""Quién ve qué (SPEC, sección 2)."""

import re

from apps.cuentas import permisos

from .conftest import asignar, cliente_de


def nombres_en_lista(html):
    return re.findall(r'class="nombre-obra( asignada)?"[^>]*>(?:<span[^>]*></span>)?([^<]+)', html)


def test_todo_el_personal_ve_todos_los_proyectos(comun, proyectos):
    respuesta = cliente_de(comun).get("/proyectos/")
    assert respuesta.status_code == 200
    assert {n for _, n in nombres_en_lista(respuesta.content.decode())} == {"Casa Lago", "Edificio Sur", "Local B"}
    for p in proyectos:
        assert cliente_de(comun).get(f"/obras/{p.pk}/").status_code == 200


def test_las_obras_solo_las_ve_su_equipo(comun, otro, obra):
    asignar(comun, obra)
    assert cliente_de(comun).get(f"/obras/{obra.pk}/").status_code == 200
    assert cliente_de(otro).get(f"/obras/{obra.pk}/").status_code == 403
    assert nombres_en_lista(cliente_de(otro).get("/obras/").content.decode()) == []


def test_coordinacion_dir_y_administracion_ven_todas_las_obras(dir_, coordinador, administracion, obra):
    for u in (dir_, coordinador, administracion):
        assert cliente_de(u).get(f"/obras/{obra.pk}/").status_code == 200, u


def test_los_asignados_aparecen_primero_y_marcados(comun, proyectos):
    asignar(comun, proyectos[2])  # Local B
    filas = nombres_en_lista(cliente_de(comun).get("/proyectos/").content.decode())
    assert filas[0] == (" asignada", "Local B")
    assert [n for _, n in filas[1:]] == ["Casa Lago", "Edificio Sur"]
    assert all(marca == "" for marca, _ in filas[1:])


def test_editar_tareas_solo_responsables_y_dir(comun, otro, dir_, obra):
    asignar(comun, obra, responsable=True)
    asignar(otro, obra)
    assert permisos.puede_editar_obra(comun, obra)
    assert permisos.puede_editar_obra(dir_, obra)
    assert not permisos.puede_editar_obra(otro, obra)
    respuesta = cliente_de(otro).post(f"/obras/{obra.pk}/tareas/", {"estructura": "[]"})
    assert respuesta.status_code == 403


def test_montos_solo_dir_y_administracion(dir_, administracion, coordinador, comun, obra):
    asignar(comun, obra, responsable=True)
    assert permisos.puede_ver_montos(dir_)
    assert permisos.puede_ver_montos(administracion)
    assert not permisos.puede_ver_montos(coordinador)
    assert not permisos.puede_ver_montos(comun)
    assert "tab=certificados" in cliente_de(administracion).get(f"/obras/{obra.pk}/").content.decode()
    for u in (coordinador, comun):
        html = cliente_de(u).get(f"/obras/{obra.pk}/?tab=certificados").content.decode()
        assert "tab=certificados" not in html
        assert "Presupuesto total" not in html


def test_historial_de_avance_solo_dir_coordinacion_y_administracion(dir_, coordinador, administracion, comun, obra):
    asignar(comun, obra, responsable=True)
    for u in (dir_, coordinador, administracion):
        assert "tab=historial" in cliente_de(u).get(f"/obras/{obra.pk}/").content.decode(), u
    html = cliente_de(comun).get(f"/obras/{obra.pk}/?tab=historial").content.decode()
    assert "tab=historial" not in html and "Historial de avance" not in html
