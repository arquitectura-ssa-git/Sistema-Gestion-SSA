import json
from datetime import date

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.adquisiciones.importar_trello import crear, items_de, leer
from apps.adquisiciones.models import Cotizacion, Pedido
from apps.cuentas.models import Area
from apps.notificaciones.models import Notificacion
from apps.obras.models import AsignacionObra, Obra

from .conftest import A, asignar, cliente_de, persona

E = Pedido.Estado


@pytest.fixture
def compras(db):
    u = persona("julieta@ssa.test", (A.GESTION_ADMINISTRATIVA, "integrante"))
    u.gestion_compras = True
    u.save()
    return u


@pytest.fixture
def dt(db, obra):
    u = persona("dt@ssa.test", (A.DIRECCION_TECNICA, "integrante"))
    AsignacionObra.objects.create(obra=obra, usuario=u, area=Area.objects.get(codigo=A.DIRECCION_TECNICA))
    return u


def _nuevo(c, obra, **extra):
    datos = {"obra": obra.pk, "tipo": "materiales", "titulo": "Cemento y cal", "urgente": "on",
             "necesario_para": "2026-11-20", "nota": "Para la losa",
             "items-TOTAL_FORMS": "2", "items-INITIAL_FORMS": "0", "items-MIN_NUM_FORMS": "0", "items-MAX_NUM_FORMS": "100",
             "items-0-descripcion": "Cemento 50 kg", "items-0-cantidad": "40", "items-0-unidad": "bolsas",
             "items-1-descripcion": "", "items-1-cantidad": "", "items-1-unidad": ""}
    datos.update(extra)
    return c.post("/adquisiciones/nuevo/", datos)


def _cotizar(c, p, proveedor, monto):
    return c.post(f"/adquisiciones/{p.pk}/cotizacion/", {"proveedor_nombre": proveedor, "monto": monto,
                                                          "detalle": "contado"})


def test_circuito_completo_de_obra_con_avisos(dt, compras, dir_, obra):
    r = _nuevo(cliente_de(dt), obra)
    assert r.status_code == 302
    p = Pedido.objects.get()
    assert p.codigo == "PED-0001" and p.estado == E.PEDIDO and p.items.count() == 1
    assert Notificacion.objects.filter(usuario=compras, texto__contains="Nuevo pedido PED-0001").exists()

    cj = cliente_de(compras)
    cj.post(f"/adquisiciones/{p.pk}/accion/cotizar/", {"proveedores": "Corralón Norte"})
    p.refresh_from_db()
    assert p.estado == E.COTIZACION
    assert Notificacion.objects.filter(usuario=dt, texto__contains="en gestión").exists()

    _cotizar(cj, p, "Corralón Norte", "1245000")
    _cotizar(cj, p, "Corralón Sur", "1318000")
    assert p.cotizaciones.count() == 2 and p.elegida.proveedor_nombre == "Corralón Norte"
    cj.post(f"/adquisiciones/{p.pk}/accion/orden/")
    cj.post(f"/adquisiciones/{p.pk}/accion/a_dir/")
    p.refresh_from_db()
    assert p.estado == E.AUTORIZACION and p.oc_numero == "OC-0001"
    assert Notificacion.objects.filter(usuario=dir_, texto__contains="espera tu autorización").exists()

    cd = cliente_de(dir_)
    assert "Espera tu autorización" in cd.get(f"/adquisiciones/{p.pk}/").content.decode()
    assert "PED-0001" in cd.get("/tablero/").content.decode()  # aparece en el Dashboard de DIR
    cd.post(f"/adquisiciones/{p.pk}/accion/autorizar/")
    p.refresh_from_db()
    assert p.estado == E.FACTURACION

    cj.post(f"/adquisiciones/{p.pk}/accion/factura/", {"factura_numero": "A-0001-123"})
    cj.post(f"/adquisiciones/{p.pk}/accion/comprado/")
    cj.post(f"/adquisiciones/{p.pk}/accion/entrega/", {"fecha_entrega": "2026-11-18", "entrega_detalle": "flete"})
    p.refresh_from_db()
    assert p.estado == E.RECEPCION and p.fecha_entrega == date(2026, 11, 18)

    cdt = cliente_de(dt)
    cdt.post(f"/adquisiciones/{p.pk}/accion/recibir/", {"completa": "no", "nota": "Faltan 10 bolsas"})
    p.refresh_from_db()
    assert p.estado == E.RECEPCION  # entrega parcial: queda abierto
    assert Notificacion.objects.filter(usuario=dir_, texto__contains="entrega parcial").exists()
    cdt.post(f"/adquisiciones/{p.pk}/accion/recibir/", {"completa": "si", "nota": ""})
    p.refresh_from_db()
    assert p.estado == E.CERRADO and p.recepciones.count() == 2
    assert p.movimientos.count() >= 10


def test_no_se_saltea_ni_lo_mueve_otro(dt, compras, dir_, obra, otro):
    _nuevo(cliente_de(dt), obra)
    p = Pedido.objects.get()
    cliente_de(dt).post(f"/adquisiciones/{p.pk}/accion/cotizar/")  # el DT no gestiona
    cliente_de(compras).post(f"/adquisiciones/{p.pk}/accion/orden/")  # salteo
    cliente_de(compras).post(f"/adquisiciones/{p.pk}/accion/autorizar/")  # Compras no autoriza
    p.refresh_from_db()
    assert p.estado == E.PEDIDO
    assert cliente_de(otro).get(f"/adquisiciones/{p.pk}/").status_code == 403  # ajeno a la obra


def test_orden_sin_cotizacion_no_avanza(compras, obra):
    p = Pedido.objects.create(obra=obra, titulo="Hierro", estado=E.COTIZACION)
    cliente_de(compras).post(f"/adquisiciones/{p.pk}/accion/orden/")
    p.refresh_from_db()
    assert p.estado == E.COTIZACION


def test_hasta_tres_cotizaciones(compras, obra):
    p = Pedido.objects.create(obra=obra, titulo="Hierro", estado=E.COTIZACION)
    c = cliente_de(compras)
    for i in range(4):
        _cotizar(c, p, f"Proveedor {i}", str(1000 + i))
    assert p.cotizaciones.count() == Cotizacion.MAXIMO


def test_dir_devuelve_con_comentario_obligatorio(dt, compras, dir_, obra):
    p = Pedido.objects.create(obra=obra, titulo="Pintura", estado=E.AUTORIZACION, creado_por=dt)
    Cotizacion.objects.create(pedido=p, proveedor_nombre="X", monto=10, elegida=True)
    cd = cliente_de(dir_)
    cd.post(f"/adquisiciones/{p.pk}/accion/devolver/", {"comentario": ""})
    p.refresh_from_db()
    assert p.estado == E.AUTORIZACION
    cd.post(f"/adquisiciones/{p.pk}/accion/devolver/", {"comentario": "Pedir otra cotización"})
    p.refresh_from_db()
    assert p.estado == E.ORDEN and p.devuelto
    assert Notificacion.objects.filter(usuario=compras, texto__contains="Pedir otra cotización").exists()
    cliente_de(compras).post(f"/adquisiciones/{p.pk}/accion/a_dir/")
    p.refresh_from_db()
    assert p.estado == E.AUTORIZACION and not p.devuelto
    cd.post(f"/adquisiciones/{p.pk}/accion/rechazar/", {"comentario": "No va"})
    p.refresh_from_db()
    assert p.estado == E.RECHAZADO and not p.abierto
    assert Notificacion.objects.filter(usuario=dt, texto__contains="rechazó").exists()


def test_pedido_de_proyecto_circuito_corto(compras, dir_, proyectos, comun):
    proyecto = proyectos[0]
    asignar(comun, proyecto, responsable=True)
    c = cliente_de(comun)
    _nuevo(c, proyecto, tipo="contratacion", titulo="Cálculo estructural")
    p = Pedido.objects.get()
    _cotizar(c, p, "Ing. Pérez", "950000")
    c.post(f"/adquisiciones/{p.pk}/accion/a_dir/")
    p.refresh_from_db()
    assert p.estado == E.AUTORIZACION
    cliente_de(dir_).post(f"/adquisiciones/{p.pk}/accion/autorizar/")
    p.refresh_from_db()
    assert p.estado == E.ORDEN
    cliente_de(compras).post(f"/adquisiciones/{p.pk}/accion/emitir/")
    p.refresh_from_db()
    assert p.estado == E.CERRADO and p.oc_numero


def test_montos_visibles_segun_quien(dt, compras, obra, comun):
    p = Pedido.objects.create(obra=obra, titulo="Hierro", estado=E.ORDEN)
    Cotizacion.objects.create(pedido=p, proveedor_nombre="Hierros SA", monto=4870000, elegida=True)
    assert "4.870.000" in cliente_de(dt).get(f"/adquisiciones/{p.pk}/").content.decode()
    assert "4.870.000" in cliente_de(compras).get("/adquisiciones/tablero/").content.decode()
    asignar(comun, obra)  # equipo de la obra: también ve los montos de sus pedidos
    assert "4.870.000" in cliente_de(comun).get(f"/adquisiciones/{p.pk}/").content.decode()


def test_pantallas_responden(compras, dir_, dt, obra):
    Pedido.objects.create(obra=obra, titulo="Hierro", estado=E.PEDIDO, creado_por=dt)
    for u in (compras, dir_, dt):
        c = cliente_de(u)
        for url in ("/adquisiciones/", "/adquisiciones/tablero/", "/adquisiciones/lista/?estado=todos",
                    "/adquisiciones/nuevo/", "/avisos/"):
            assert c.get(url).status_code == 200, (u, url)
    assert "Mis pendientes" in cliente_de(compras).get("/adquisiciones/").content.decode()


def test_solo_dir_marca_gestion_compras(coordinador, comun):
    r = cliente_de(coordinador).get(f"/personal/{comun.pk}/editar/")
    assert r.status_code == 200 and "gestion_compras" not in r.content.decode()


TABLERO = {
    "name": "OBRA X - Acceso",
    "lists": [{"id": "l1", "name": "01-REQ. DE OBRA-DT"}, {"id": "l3", "name": "03-COTIZACION-OT"},
              {"id": "l7", "name": "07-FINALIZADA-ADM"}, {"id": "l0", "name": "00-PEDIDOS MAL REALIZADOS"}],
    "cards": [
        {"id": "65000000aaaaaaaaaaaaaaaa", "name": "REQ Nº 009 Botines de seguridad", "idList": "l1",
         "desc": "Listado de Materiales y/o recursos solicitados:\n\n1 PAR DE BOTINES TALLE 45\n2 cascos",
         "due": "2026-10-15T17:52:00.000Z", "closed": False, "attachments": [], "shortUrl": "https://trello.com/c/x"},
        {"id": "65000001aaaaaaaaaaaaaaaa", "name": "REQ Nº 010 Instalación sanitaria", "idList": "l3", "desc": "",
         "closed": False, "attachments": [{"name": "presupuesto.pdf", "url": "https://trello.com/a.pdf"}]},
        {"id": "65000002aaaaaaaaaaaaaaaa", "name": "Viejo", "idList": "l7", "desc": "", "closed": True},
        {"id": "65000003aaaaaaaaaaaaaaaa", "name": "Mal pedido", "idList": "l0", "desc": "", "closed": False},
    ],
    "actions": [{"type": "commentCard", "date": "2026-10-10T12:00:00.000Z",
                 "data": {"card": {"id": "65000000aaaaaaaaaaaaaaaa"}, "text": "Pedí 3 presupuestos"},
                 "memberCreator": {"fullName": "Julieta"}}],
}


def test_items_desde_la_descripcion():
    items = items_de("Listado de Materiales y/o recursos solicitados:\n\n1 PAR DE BOTINES\n20 litros aceite\nTornillos")
    assert items[0] == {"descripcion": "BOTINES", "cantidad": 1, "unidad": "par"}
    assert items[1]["unidad"] == "litros" and items[1]["cantidad"] == 20
    assert items[2] == {"descripcion": "Tornillos", "cantidad": None, "unidad": ""}


def test_importar_trello(obra, compras):
    leido = leer(json.dumps(TABLERO))
    assert len(leido["filas"]) == 3  # la archivada no entra
    assert crear(obra, leido["filas"], compras) == 3
    assert crear(obra, leido["filas"], compras) == 0  # no se repite
    botines = Pedido.objects.get(titulo="Botines de seguridad")
    assert botines.estado == E.PEDIDO and botines.necesario_para == date(2026, 10, 15)
    assert botines.items.count() == 2 and "REQ 009" in botines.nota
    assert botines.movimientos.filter(comentario="Pedí 3 presupuestos").exists()
    assert Pedido.objects.get(titulo="Instalación sanitaria").estado == E.COTIZACION
    assert Pedido.objects.get(titulo="Mal pedido").estado == E.RECHAZADO


def test_importar_trello_por_pantalla(obra, compras):
    c = cliente_de(compras)
    archivo = SimpleUploadedFile("tablero.json", json.dumps(TABLERO).encode(), content_type="application/json")
    r = c.post("/adquisiciones/importar-trello/", {"obra": obra.pk, "archivo": archivo})
    assert "Importar 3 pedidos" in r.content.decode()
    c.post("/adquisiciones/importar-trello/", {"confirmar": "1"})
    assert Pedido.objects.filter(obra=obra).count() == 3
