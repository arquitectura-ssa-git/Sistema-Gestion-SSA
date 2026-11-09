"""Informe diario de Dirección Técnica: lo que pasó en la obra cada día (clima, personal por gremio, avance, fotos,
notas de pedido del libro de obra y observaciones). Se carga el mismo día hasta las 23:59; corregirlo después
requiere la autorización de DIR."""

import uuid

from django.conf import settings
from django.db import models


class Gremio(models.Model):
    """Lista de gremios para contar el personal en obra. La editan los DT y Coordinación de Obras."""

    nombre = models.CharField(max_length=60, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class InformeDiario(models.Model):
    class Clima(models.TextChoices):
        SOL = "sol", "Sol"
        LLUVIA = "lluvia", "Lluvia"

    obra = models.ForeignKey("obras.Obra", on_delete=models.CASCADE, related_name="informes")
    fecha = models.DateField()
    clima = models.CharField(max_length=10, choices=Clima.choices, default=Clima.SOL)
    se_trabajo = models.BooleanField("se pudo trabajar en obra", default=True)  # se pregunta solo si llueve
    motivo_sin_trabajo = models.CharField("por qué no se trabajó", max_length=200, blank=True)
    notas_pedido = models.TextField("notas de pedido (libro de obra)", blank=True)
    observaciones = models.TextField(blank=True)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha"]
        constraints = [models.UniqueConstraint(fields=["obra", "fecha"], name="un_informe_por_obra_y_dia")]

    def __str__(self):
        return f"{self.obra.nombre} · {self.fecha:%d/%m/%Y}"

    @property
    def personas(self):
        return sum(p.cantidad for p in self.personal.all())


class PersonalGremio(models.Model):
    informe = models.ForeignKey(InformeDiario, on_delete=models.CASCADE, related_name="personal")
    gremio = models.ForeignKey(Gremio, on_delete=models.PROTECT, related_name="+")
    cantidad = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["gremio__orden", "gremio__nombre"]
        constraints = [models.UniqueConstraint(fields=["informe", "gremio"], name="un_gremio_por_informe")]


def ruta_foto(instancia, nombre):
    return f"informes/{instancia.informe.obra_id}/{instancia.informe.fecha:%Y-%m-%d}-{uuid.uuid4().hex[:10]}.jpg"


class FotoInforme(models.Model):
    """Foto de una tarea en ejecución, o de la hoja del libro de obra con la nota de pedido (`del_libro`)."""

    informe = models.ForeignKey(InformeDiario, on_delete=models.CASCADE, related_name="fotos")
    archivo = models.ImageField(upload_to=ruta_foto)
    del_libro = models.BooleanField("hoja del libro de obra", default=False)
    detalle = models.CharField(max_length=200, blank=True)
    tarea = models.ForeignKey("obras.TareaObra", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["creada", "id"]


class HabilitacionInforme(models.Model):
    """Pedido para cargar o corregir el informe de un día que ya cerró. Lo resuelve DIR; si lo aprueba, ese día
    queda abierto hasta las 23:59 del día en que se aprobó."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    obra = models.ForeignKey("obras.Obra", on_delete=models.CASCADE, related_name="habilitaciones_informe")
    fecha = models.DateField("día del informe")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    motivo = models.CharField(max_length=300)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    pedida = models.DateTimeField(auto_now_add=True)
    resuelta_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    resuelta = models.DateTimeField(null=True, blank=True)
    valida_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-pedida"]

    def __str__(self):
        return f"{self.obra.nombre} · {self.fecha:%d/%m/%Y} · {self.get_estado_display()}"
