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


def test_montos_dir_administracion_y_coordinacion_de_proyectos(dir_, administracion, coordinador, coord_obras,
                                                                 comun, obra):
    asignar(comun, obra, responsable=True)
    for u in (dir_, administracion, coordinador):
        assert permisos.puede_ver_montos(u)
        assert "tab=certificados" in cliente_de(u).get(f"/obras/{obra.pk}/").content.decode()
    assert not permisos.puede_ver_montos(coord_obras)
    assert not permisos.puede_ver_montos(comun)
    for u in (coord_obras, comun):
        html = cliente_de(u).get(f"/obras/{obra.pk}/?tab=certificados").content.decode()
        assert "tab=certificados" not in html
        assert "Presupuesto total" not in html


def test_historial_de_avance_solo_dir_coordinacion_y_administracion(dir_, coordinador, administracion, comun, obra):
    asignar(comun, obra, responsable=True)
    for u in (dir_, coordinador, administracion):
        assert "tab=historial" in cliente_de(u).get(f"/obras/{obra.pk}/").content.decode(), u
    html = cliente_de(comun).get(f"/obras/{obra.pk}/?tab=historial").content.decode()
    assert "tab=historial" not in html and "Historial de avance" not in html


def test_dashboard_de_dir_resume_las_horas_por_proyecto(dir_, comun, proyectos):
    from datetime import date

    from apps.horas.models import RegistroHoras

    for p, horas in ((proyectos[0], 6), (proyectos[1], 2)):
        RegistroHoras.objects.create(usuario=comun, fecha=date.today(), obra=p, horas=horas)
    RegistroHoras.objects.create(usuario=comun, fecha=date.today(), obra=proyectos[0], horas=1.5, extra=True)
    html = cliente_de(dir_).get("/tablero/").content.decode()
    assert "Resumen TR" in html
    assert "Time Report de hoy" not in html  # DIR no carga horas
    assert html.index("Casa Lago") < html.index("Edificio Sur")  # de más a menos horas
    assert "7,5 h" in html and "1,5 h" in html
    html_comun = cliente_de(comun).get("/tablero/").content.decode()
    assert "Resumen TR" not in html_comun and "Time Report de hoy" in html_comun


def test_filtrar_proyectos_por_tipo(comun, proyectos):
    proyectos[0].uso = "residencial"
    proyectos[0].save()
    proyectos[1].uso = "comercial"
    proyectos[1].save()
    html = cliente_de(comun).get("/proyectos/?uso=residencial").content.decode()
    assert [n for _, n in nombres_en_lista(html)] == ["Casa Lago"]
    assert "Residencial" in html


def test_coordinacion_de_proyectos_edita_todos_los_proyectos_y_obras(coordinador, proyectos, obra):
    # coordinador = responsable de Gestión de Proyectos, sin estar asignado a nada
    for o in (proyectos[0], obra):
        assert permisos.puede_editar_obra(coordinador, o)
        assert cliente_de(coordinador).get(f"/obras/{o.pk}/editar/").status_code == 200
    r = cliente_de(coordinador).post(f"/obras/{obra.pk}/tareas/", {"estructura": "[]"})
    assert r.status_code == 302


def test_coordinacion_de_obras_no_edita_lo_ajeno(obra):
    from .conftest import A, persona

    coord_obras = persona("cobras@ssa.test", (A.GESTION_OBRAS, "responsable"))
    assert not permisos.puede_editar_obra(coord_obras, obra)


def test_coordinacion_de_proyectos_crea_gestiona_clientes_y_lee_informes(coordinador, obra):
    c = cliente_de(coordinador)
    assert c.get("/proyectos/nuevo/").status_code == 200
    assert c.get("/personal/clientes/").status_code == 200
    assert permisos.puede_ver_informes(coordinador, obra) and not permisos.puede_cargar_informe(coordinador, obra)


def test_coordinacion_de_proyectos_da_de_alta_personal_pero_no_toca_gerencia(coordinador, dir_, comun):
    from apps.cuentas.models import Usuario

    c = cliente_de(coordinador)
    html = c.get("/personal/nueva/").content.decode()
    assert c.get("/personal/nueva/").status_code == 200 and "area_gerencia" not in html
    r = c.post("/personal/nueva/", {"first_name": "Nueva", "last_name": "Persona", "email": "nueva@ssa.test",
                                    "area_desarrollo_proyectos": "integrante", "area_gerencia": "responsable",
                                    "is_active": "on"})
    assert r.status_code == 302
    nueva = Usuario.objects.get(email="nueva@ssa.test")
    assert list(nueva.membresias.values_list("area__codigo", flat=True)) == ["desarrollo_proyectos"]
    assert c.get(f"/personal/{dir_.pk}/editar/").status_code == 403
    assert c.get(f"/personal/{comun.pk}/editar/").status_code == 200
    assert cliente_de(comun).get("/personal/nueva/").status_code == 403
