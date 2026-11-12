"""Asistente de Dirección: ve proyectos, obras, avances, informes e historial sin montos; no carga Time Report y su
jornada se computa sola (como Administración), salvo los días que DIR marca como ausencia."""

from datetime import timedelta

import pytest

from apps.cuentas import permisos
from apps.horas import reglas
from apps.horas.models import Ausencia, RegistroHoras

from .conftest import A, cliente_de, persona


@pytest.fixture
def asistente(db):
    u = persona("asistente@ssa.test", (A.GESTION_ADMINISTRATIVA, "integrante"))
    u.asistente_direccion = True
    u.tr_automatico_desde = reglas.hoy() - timedelta(days=13)
    u.save()
    return u


def test_ve_obras_avances_e_informes_pero_no_montos(asistente, obra):
    assert permisos.puede_ver_obra(asistente, obra)
    assert permisos.puede_ver_historial_avance(asistente) and permisos.puede_ver_informes(asistente, obra)
    assert not permisos.puede_ver_montos(asistente) and not permisos.puede_editar_obra(asistente, obra)
    html = cliente_de(asistente).get(f"/obras/{obra.pk}/").content.decode()
    assert "tab=historial" in html and "tab=informes" in html and "tab=certificados" not in html
    assert permisos.puede_gestionar_clientes(asistente) and permisos.puede_ver_legajos(asistente)


def test_no_carga_horas_y_su_jornada_se_computa_sola(asistente):
    c = cliente_de(asistente)
    html = c.get("/horas/").content.decode()
    assert "Tu jornada se computa sola" in html and "Guardar horas" not in html
    regs = RegistroHoras.objects.filter(usuario=asistente, automatico=True)
    habiles = sum(1 for i in range(14) if (reglas.hoy() - timedelta(days=i)).weekday() < 5
                  and not reglas.feriado(reglas.hoy() - timedelta(days=i)))
    assert regs.count() == habiles and all(r.tipo == "administracion" and r.horas == 8 for r in regs)
    reglas.completar_automaticos()
    assert regs.count() == habiles  # no duplica


def test_dir_marca_una_ausencia_y_ese_dia_no_se_computa(asistente, dir_):
    reglas.completar_automaticos()
    dia = RegistroHoras.objects.filter(usuario=asistente).order_by("fecha").first().fecha
    cliente_de(dir_).post(f"/horas/ausencia/{asistente.pk}/", {"dia": dia.isoformat()})
    assert Ausencia.objects.filter(usuario=asistente, fecha=dia).exists()
    reglas.completar_automaticos()
    assert not RegistroHoras.objects.filter(usuario=asistente, fecha=dia).exists()
    cliente_de(dir_).post(f"/horas/ausencia/{asistente.pk}/", {"dia": dia.isoformat()})  # quitar la ausencia
    assert RegistroHoras.objects.filter(usuario=asistente, fecha=dia, automatico=True).exists()


def test_solo_dir_asigna_el_perfil(coordinador, dir_):
    assert "asistente_direccion" not in cliente_de(coordinador).get("/personal/nueva/").content.decode()
    assert "asistente_direccion" in cliente_de(dir_).get("/personal/nueva/").content.decode()
