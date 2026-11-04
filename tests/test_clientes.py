"""Clientes: apellido o razón social en mayúsculas y nombre con inicial mayúscula."""

from apps.cuentas.models import Cliente

from .conftest import cliente_de


def test_apellido_en_mayusculas_y_nombre_con_inicial(dir_):
    r = cliente_de(dir_).post("/personal/clientes/nuevo/", {"apellido": "navarro  vittar", "nombres": "ana MAGDALENA"})
    assert r.status_code == 302
    c = Cliente.objects.get()
    assert (c.apellido, c.nombres, str(c)) == ("NAVARRO VITTAR", "Ana Magdalena", "NAVARRO VITTAR, Ana Magdalena")


def test_una_empresa_va_sin_nombre(dir_):
    cliente_de(dir_).post("/personal/clientes/nuevo/", {"apellido": "Constructora Sur S.A."})
    assert str(Cliente.objects.get()) == "CONSTRUCTORA SUR S.A."


def test_el_apellido_es_obligatorio(dir_):
    html = cliente_de(dir_).post("/personal/clientes/nuevo/", {"nombres": "Ana"}).content.decode()
    assert "Apellido o razón social" in html and not Cliente.objects.exists()
