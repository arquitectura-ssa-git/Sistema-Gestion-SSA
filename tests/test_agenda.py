"""Agenda: la gestionan DIR, Coordinación de Proyectos y Administración (con Asistente de Dirección); los clientes se
sincronizan con Clientes en los dos sentidos."""

from apps.agenda.models import Contacto, TipoContacto
from apps.cuentas.models import Cliente

from .conftest import cliente_de


def proveedor():
    return TipoContacto.objects.get(codigo="proveedor")


def test_quien_entra(dir_, coordinador, administracion, comun, coord_obras):
    for u in (dir_, coordinador, administracion):
        assert cliente_de(u).get("/agenda/").status_code == 200
        assert 'href="/agenda/"' in cliente_de(u).get("/tablero/").content.decode()
    for u in (comun, coord_obras):
        assert cliente_de(u).get("/agenda/").status_code == 403


def test_un_cliente_nuevo_aparece_en_la_agenda(dir_):
    cliente_de(dir_).post("/personal/clientes/nuevo/", {"apellido": "santos", "nombres": "juan", "cuit": "20-1-3"})
    c = Contacto.objects.get(cliente__apellido="SANTOS")
    assert (c.tipo.codigo, c.apellido, c.nombres, c.cuit) == ("cliente", "SANTOS", "Juan", "20-1-3")
    cliente = Cliente.objects.get()
    cliente.telefono = "+54 381 1"
    cliente.save()
    c.refresh_from_db()
    assert c.telefono == "+54 381 1" and Contacto.objects.count() == 1


def test_un_contacto_de_tipo_cliente_crea_el_cliente(administracion):
    tipo = TipoContacto.objects.get(codigo="cliente")
    r = cliente_de(administracion).post("/agenda/nuevo/", {"tipo": tipo.pk, "empresa": "Paramerica SA",
                                                           "apellido": "lopez", "nombres": "ana", "email": "a@p.com",
                                                           "cbu": "000123", "alias": "para.merica"})
    assert r.status_code == 302
    cliente = Cliente.objects.get()
    assert (cliente.apellido, cliente.nombres, cliente.email) == ("PARAMERICA SA", "", "a@p.com")
    c = Contacto.objects.get()
    assert (c.cliente, c.apellido, c.nombres, c.cbu) == (cliente, "LOPEZ", "Ana", "000123")


def test_proveedores_filtros_y_tipos_nuevos(dir_):
    Contacto.objects.create(tipo=proveedor(), empresa="Hormigones del Norte", apellido="gomez", nombres="martin")
    c = cliente_de(dir_)
    html = c.get("/agenda/?tipo=proveedor").content.decode()
    assert "Hormigones del Norte" in html and "GOMEZ, Martin" in html
    assert "Hormigones del Norte" not in c.get("/agenda/?tipo=cliente").content.decode()
    assert dir_.email in c.get("/agenda/?tipo=equipo").content.decode()
    c.post("/agenda/tipos/", {"nombre": "Organismos"})
    assert TipoContacto.objects.filter(codigo="organismos").exists()
    assert "Organismos" in c.get("/agenda/").content.decode()


def test_eliminar_un_contacto_cliente_con_obras_no_se_permite(dir_):
    from apps.obras.models import Obra

    cliente = Cliente.objects.create(apellido="PEREZ")
    Obra.objects.create(tipo=Obra.Tipo.OBRA, nombre="Casa", cliente=cliente)
    contacto = Contacto.objects.get(cliente=cliente)
    cliente_de(dir_).post(f"/agenda/{contacto.pk}/eliminar/")
    assert Contacto.objects.filter(pk=contacto.pk).exists() and Cliente.objects.exists()
    otro = Contacto.objects.create(tipo=proveedor(), empresa="X")
    cliente_de(dir_).post(f"/agenda/{otro.pk}/eliminar/")
    assert not Contacto.objects.filter(pk=otro.pk).exists()
