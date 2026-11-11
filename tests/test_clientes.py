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


def test_eliminar_un_cliente_sin_trabajos(dir_):
    c = Cliente.objects.create(apellido="SANTOS", nombres="Juan")
    r = cliente_de(dir_).post(f"/personal/clientes/{c.pk}/eliminar/")
    assert r.status_code == 302 and not Cliente.objects.exists()
    from apps.auditoria.models import RegistroActividad

    assert RegistroActividad.objects.filter(accion="cliente.baja", descripcion__contains="SANTOS").exists()


def test_no_se_elimina_un_cliente_con_obras_aunque_esten_en_la_papelera(dir_, comun):
    from apps.obras.models import Obra

    c = Cliente.objects.create(apellido="PEREZ")
    Obra.objects.create(tipo=Obra.Tipo.OBRA, nombre="Casa", cliente=c, eliminada=True)
    assert cliente_de(dir_).post(f"/personal/clientes/{c.pk}/eliminar/").status_code == 302
    assert Cliente.objects.filter(pk=c.pk).exists()
    assert cliente_de(comun).post(f"/personal/clientes/{c.pk}/eliminar/").status_code == 403
