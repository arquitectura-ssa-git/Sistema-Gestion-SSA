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


class NodoTarea(models.Model):
    """Una fila del listado de tareas: etapa, rubro o ítem.

    Etapa → rubros → ítems (un rubro puede no tener ítems y no hace falta usar etapas).
    La incidencia es el porcentaje dentro de su grupo (sus hermanos); el peso en el total
    sale de multiplicar las incidencias de toda la rama.
    """

    class Tipo(models.TextChoices):
        ETAPA = "etapa", "Etapa"
        RUBRO = "rubro", "Rubro"
        ITEM = "item", "Ítem"

    tipo = models.CharField(max_length=5, choices=Tipo.choices, default=Tipo.RUBRO)
    padre = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="hijos")
    nombre = models.CharField(max_length=300)
    incidencia = models.DecimalField("incidencia (%)", max_digits=6, decimal_places=3,
                                     validators=[MinValueValidator(Decimal("0.001")), MaxValueValidator(100)])
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        abstract = True
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.incidencia:g}%)"


class TareaPlantilla(NodoTarea):
    plantilla = models.ForeignKey(Plantilla, on_delete=models.CASCADE, related_name="tareas")

    class Meta(NodoTarea.Meta):
        verbose_name = "tarea de plantilla"
        verbose_name_plural = "tareas de plantilla"
