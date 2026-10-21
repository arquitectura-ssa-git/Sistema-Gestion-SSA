from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class RegistroHoras(models.Model):
    """Horas que una persona dedicó un día a un proyecto u obra (o al estudio), por tipo de tarea."""

    class Tipo(models.TextChoices):
        PRODUCCION = "produccion", "Producción"
        GESTION = "gestion", "Gestión"
        ADMINISTRACION = "administracion", "Administración"
        COMPRAS = "compras", "Compras"
        CAPACITACION = "capacitacion", "Capacitación"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="horas")
    fecha = models.DateField(db_index=True)
    obra = models.ForeignKey("obras.Obra", null=True, blank=True, on_delete=models.PROTECT, related_name="horas",
                             verbose_name="proyecto u obra", help_text="Vacío = trabajo del estudio, sin proyecto.")
    tipo = models.CharField("tipo de tarea", max_length=20, choices=Tipo.choices, default=Tipo.PRODUCCION)
    horas = models.DecimalField(max_digits=4, decimal_places=1,
                                validators=[MinValueValidator(Decimal("0.5")), MaxValueValidator(24)])
    extra = models.BooleanField("hora extra", default=False)
    nota = models.CharField(max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "registro de horas"
        verbose_name_plural = "registros de horas"
        ordering = ["fecha", "id"]

    def __str__(self):
        return f"{self.usuario} · {self.fecha:%d/%m/%Y} · {self.obra or 'Estudio'} · {self.horas:g} h"


class Habilitacion(models.Model):
    """Pedido para cargar o corregir horas de un día pasado. Si se aprueba, ese día queda abierto
    hasta las 23:59 del día en que se aprobó."""

    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADA = "aprobada", "Aprobada"
        RECHAZADA = "rechazada", "Rechazada"

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="habilitaciones")
    fecha = models.DateField("día a cargar")
    motivo = models.CharField(max_length=300)
    estado = models.CharField(max_length=10, choices=Estado.choices, default=Estado.PENDIENTE)
    pedida = models.DateTimeField(auto_now_add=True)
    resuelta_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    resuelta = models.DateTimeField(null=True, blank=True)
    valida_hasta = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "habilitación de carga"
        verbose_name_plural = "habilitaciones de carga"
        ordering = ["-pedida"]

    def __str__(self):
        return f"{self.usuario} · {self.fecha:%d/%m/%Y} · {self.get_estado_display()}"
