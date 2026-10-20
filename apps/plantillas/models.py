from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Plantilla(models.Model):
    """Listado modelo de tareas con su incidencia. Al aplicarla a un proyecto u obra, las tareas se copian."""

    class Uso(models.TextChoices):
        PROYECTO = "proyecto", "Proyectos"
        OBRA = "obra", "Obras"
        AMBOS = "ambos", "Proyectos y obras"

    nombre = models.CharField(max_length=150, unique=True)
    descripcion = models.TextField("descripción", blank=True)
    uso = models.CharField("para", max_length=10, choices=Uso.choices, default=Uso.AMBOS)
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    def sirve_para(self, tipo):
        return self.uso in (self.Uso.AMBOS, tipo)


class TareaPlantilla(models.Model):
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE, related_name="tareas")
    nombre = models.CharField(max_length=200)
    incidencia = models.DecimalField("incidencia (%)", max_digits=5, decimal_places=2,
                                     validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(100)])
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "tarea de plantilla"
        verbose_name_plural = "tareas de plantilla"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.incidencia:g}%)"
