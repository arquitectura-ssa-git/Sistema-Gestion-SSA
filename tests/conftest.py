"""Datos de prueba comunes: una persona por rol y un par de proyectos y obras.

Las pruebas corren sobre una base vacía que se crea sola (con las 6 áreas que trae la migración inicial).
"""

import pytest
from django.test import Client

from apps.cuentas.models import Area, MiembroArea, Usuario
from apps.obras.models import AsignacionObra, Obra

A = Area.Codigo


@pytest.fixture(autouse=True)
def _archivos_temporales(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.ALLOWED_HOSTS = ["testserver"]


def persona(email, *areas):
    """areas: pares (código de área, rol)."""
    u = Usuario.objects.create_user(email, "clave-de-prueba", first_name=email.split("@")[0].capitalize(),
                                    tipo=Usuario.Tipo.PERSONAL)
    for codigo, rol in areas:
        MiembroArea.objects.create(usuario=u, area=Area.objects.get(codigo=codigo), rol=rol)
    return u


@pytest.fixture
def dir_(db):
    return persona("dir@ssa.test", (A.GERENCIA, "responsable"))


@pytest.fixture
def coordinador(db):
    return persona("coord@ssa.test", (A.GESTION_PROYECTOS, "responsable"))


@pytest.fixture
def administracion(db):
    return persona("admin@ssa.test", (A.GESTION_ADMINISTRATIVA, "responsable"))


@pytest.fixture
def comun(db):
    return persona("comun@ssa.test", (A.DESARROLLO_PROYECTOS, "integrante"))


@pytest.fixture
def otro(db):
    return persona("otro@ssa.test", (A.DESARROLLO_PROYECTOS, "integrante"))


@pytest.fixture
def proyectos(db):
    return [Obra.objects.create(tipo=Obra.Tipo.PROYECTO, nombre=n) for n in ("Casa Lago", "Edificio Sur", "Local B")]


@pytest.fixture
def obra(db):
    return Obra.objects.create(tipo=Obra.Tipo.OBRA, nombre="Casa Pérez")


def asignar(usuario, obra, responsable=False):
    return AsignacionObra.objects.create(obra=obra, usuario=usuario, area=Area.objects.get(codigo=A.DESARROLLO_PROYECTOS),
                                         es_responsable=responsable)


def cliente_de(usuario):
    c = Client()
    c.force_login(usuario)
    return c
