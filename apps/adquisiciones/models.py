"""Gestión de Adquisiciones: pedidos de materiales, contrataciones y presupuestos de una obra o un proyecto.

Circuito de obra: el DT carga el pedido → Gestión de Compras pide cotizaciones (hasta 3), elige una y arma la orden
de compra → DIR autoriza, devuelve o rechaza → factura → compra → entrega → el DT registra la recepción (una entrega
parcial deja el pedido abierto hasta completarse). Circuito de proyecto: el Responsable carga el pedido con el
presupuesto → DIR → Compras emite la orden de compra."""

import uuid

from django.conf import settings
from django.db import models


def _ruta(instance, filename):
    extension = filename.rsplit(".", 1)[-1].lower()[:8] if "." in filename else "bin"
    return f"adquisiciones/{uuid.uuid4().hex}.{extension}"


class Pedido(models.Model):
    class Tipo(models.TextChoices):
        MATERIALES = "materiales", "Materiales"
        CONTRATACION = "contratacion", "Contratación"
        PRESUPUESTO = "presupuesto", "Presupuesto"

    class Estado(models.TextChoices):
        PEDIDO = "pedido", "Recepción de pedido"
        COTIZACION = "cotizacion", "Solicitud de cotización"
        ORDEN = "orden", "Orden de compra"
        AUTORIZACION = "autorizacion", "Autorización DIR"
        FACTURACION = "facturacion", "Facturación"
        COMPRA = "compra", "Compra"
        LOGISTICA = "logistica", "Logística y entrega"
        RECEPCION = "recepcion", "Recepción en obra"
        CERRADO = "cerrado", "Completo"
        RECHAZADO = "rechazado", "Rechazado"

    codigo = models.CharField("código", max_length=12, unique=True, blank=True)
    obra = models.ForeignKey("obras.Obra", on_delete=models.PROTECT, related_name="pedidos")
    tipo = models.CharField(max_length=15, choices=Tipo.choices, default=Tipo.MATERIALES)
    titulo = models.CharField("qué se pide", max_length=150)
    estado = models.CharField(max_length=15, choices=Estado.choices, default=Estado.PEDIDO)
    urgente = models.BooleanField(default=False)
    necesario_para = models.DateField("lo necesito para el", null=True, blank=True)
    nota = models.TextField("nota para Compras", blank=True)
    devuelto = models.BooleanField(default=False)  # DIR lo devolvió para corregir y todavía no se reenvió
    proveedores_consultados = models.CharField(max_length=300, blank=True)
    oc_numero = models.CharField("orden de compra", max_length=12, blank=True)
    factura_numero = models.CharField("número de factura", max_length=40, blank=True)
    factura_archivo = models.FileField(upload_to=_ruta, blank=True)
    fecha_entrega = models.DateField("fecha de entrega", null=True, blank=True)
    entrega_detalle = models.CharField("quién lo lleva", max_length=150, blank=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="pedidos")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    estado_desde = models.DateTimeField(null=True, blank=True)
    trello_id = models.CharField(max_length=40, blank=True, db_index=True)  # tarjeta de Trello de la que vino

    class Meta:
        ordering = ["-creado"]

    def __str__(self):
        return f"{self.codigo} · {self.titulo}"

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = _siguiente("PED", Pedido.objects.values_list("codigo", flat=True))
        super().save(*args, **kwargs)

    @property
    def es_de_proyecto(self):
        return self.obra.tipo == self.obra.Tipo.PROYECTO

    @property
    def abierto(self):
        return self.estado not in (self.Estado.CERRADO, self.Estado.RECHAZADO)

    @property
    def elegida(self):
        return next((c for c in self.cotizaciones.all() if c.elegida), None)

    @property
    def monto(self):
        c = self.elegida
        return c.monto if c else None


def _siguiente(prefijo, existentes):
    numeros = [int(c.split("-")[1]) for c in existentes if c and c.startswith(prefijo + "-") and c.split("-")[1].isdigit()]
    return f"{prefijo}-{(max(numeros, default=0) + 1):04d}"


def siguiente_oc():
    return _siguiente("OC", Pedido.objects.values_list("oc_numero", flat=True))


class ItemPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    descripcion = models.CharField("descripción", max_length=200)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    unidad = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.descripcion


class Cotizacion(models.Model):
    MAXIMO = 3

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="cotizaciones")
    proveedor = models.ForeignKey("agenda.Contacto", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    proveedor_nombre = models.CharField("proveedor", max_length=150)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    detalle = models.CharField("condiciones", max_length=200, blank=True)
    archivo = models.FileField(upload_to=_ruta, blank=True)
    nombre_archivo = models.CharField(max_length=200, blank=True)
    elegida = models.BooleanField(default=False)
    cargada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monto", "id"]

    def __str__(self):
        return f"{self.proveedor_nombre} · {self.monto}"


class Adjunto(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="adjuntos")
    archivo = models.FileField(upload_to=_ruta)
    nombre = models.CharField(max_length=200, blank=True)
    es_foto = models.BooleanField(default=False)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Recepcion(models.Model):
    """Lo que el DT recibió en obra. Si falta algo, el pedido queda abierto hasta que llegue el resto."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="recepciones")
    completa = models.BooleanField(default=True)
    nota = models.TextField(blank=True)
    foto = models.FileField(upload_to=_ruta, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha"]


class Movimiento(models.Model):
    """Historial del pedido: cada cambio de estado, con quién, cuándo y el comentario."""

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="movimientos")
    texto = models.CharField(max_length=300)
    comentario = models.TextField(blank=True)
    desde = models.CharField(max_length=15, blank=True)
    hacia = models.CharField(max_length=15, blank=True)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
