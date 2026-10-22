"""Eliminar proyectos y obras: van a la papelera (solo Gerencia) y se pueden restaurar."""

from apps.auditoria.models import RegistroActividad
from apps.obras.models import Obra

from .conftest import asignar, cliente_de


def test_solo_dir_puede_eliminar(coordinador, comun, obra):
    asignar(comun, obra, responsable=True)
    for u in (coordinador, comun):
        assert cliente_de(u).post(f"/obras/{obra.pk}/eliminar/").status_code == 403
    obra.refresh_from_db()
    assert not obra.eliminada


def test_lo_eliminado_desaparece_de_todos_lados_y_se_puede_restaurar(dir_, comun, proyectos):
    proyecto = proyectos[0]
    asignar(comun, proyecto)
    c = cliente_de(dir_)
    assert c.post(f"/obras/{proyecto.pk}/eliminar/").status_code == 302
    proyecto.refresh_from_db()
    assert proyecto.eliminada and proyecto.eliminada_por == dir_
    for u in (dir_, comun):
        assert proyecto.nombre not in cliente_de(u).get("/proyectos/").content.decode()
        assert proyecto.nombre not in cliente_de(u).get("/tablero/").content.decode()
        assert proyecto.nombre not in cliente_de(u).get("/horas/").content.decode()  # Time Report
    assert cliente_de(comun).get(f"/obras/{proyecto.pk}/").status_code in (403, 404)
    assert proyecto.nombre in c.get("/obras/papelera/").content.decode()

    assert c.post(f"/obras/{proyecto.pk}/restaurar/").status_code == 302
    proyecto.refresh_from_db()
    assert not proyecto.eliminada
    assert proyecto.nombre in cliente_de(comun).get("/proyectos/").content.decode()


def test_eliminar_no_borra_datos_ni_el_registro_de_actividad(dir_, obra):
    cliente_de(dir_).post(f"/obras/{obra.pk}/eliminar/")
    assert Obra.objects.filter(pk=obra.pk).exists()
    assert RegistroActividad.objects.filter(accion="obra.eliminada").exists()
