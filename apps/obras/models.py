from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse


class Obra(models.Model):
    """Un proyecto (trabajo de diseño, planos, trámites) o una obra (construcción).

    Los dos comparten todo (equipo, hitos, archivos, tareas); el tipo se elige al crearlo.
    """

    class Tipo(models.TextChoices):
        PROYECTO = "proyecto", "Proyecto"
        OBRA = "obra", "Obra"

    class Etapa(models.TextChoices):
        ANTEPROYECTO = "anteproyecto", "Anteproyecto"
        PROYECTO = "proyecto", "Proyecto"
        DOCUMENTACION = "documentacion", "Documentación"
        LICITACION = "licitacion", "Licitación"
        EJECUCION = "ejecucion", "En ejecución"
        ENTREGA = "entrega", "Entrega"

    class Estado(models.TextChoices):
        ACTIVA = "activa", "Activa"
        PAUSADA = "pausada", "Pausada"
        FINALIZADA = "finalizada", "Finalizada"

    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.OBRA)
    codigo = models.CharField("código", max_length=20, unique=True, blank=True,
                              help_text="Si lo dejás vacío se genera solo (PR-AÑO-NNN o OB-AÑO-NNN).")
    nombre = models.CharField(max_length=200)
    cliente = models.ForeignKey("cuentas.Cliente", on_delete=models.PROTECT, related_name="obras")
    direccion = models.CharField("dirección", max_length=200, blank=True)
    localidad = models.CharField(max_length=100, blank=True)
    descripcion = models.TextField("descripción", blank=True)
    superficie_m2 = models.DecimalField("superficie (m²)", max_digits=10, decimal_places=2, null=True, blank=True)
    etapa = models.CharField(max_length=20, choices=Etapa.choices, default=Etapa.ANTEPROYECTO)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.ACTIVA)
    fecha_inicio = models.DateField("fecha de inicio", null=True, blank=True)
    fecha_fin_estimada = models.DateField("fin estimado", null=True, blank=True)
    avance = models.PositiveSmallIntegerField("avance (%)", default=0, validators=[MaxValueValidator(100)])
    equipo = models.ManyToManyField(settings.AUTH_USER_MODEL, through="AsignacionObra", related_name="obras")
    creada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name="+")
    creada = models.DateTimeField(auto_now_add=True)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creada"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}" if self.codigo else self.nombre

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = self._siguiente_codigo(self.tipo)
        super().save(*args, **kwargs)

    @property
    def es_proyecto(self):
        return self.tipo == self.Tipo.PROYECTO

    @property
    def etiqueta(self):
        """'proyecto' u 'obra', para armar textos."""
        return self.get_tipo_display().lower()

    @property
    def url_lista(self):
        return reverse("proyectos:lista" if self.es_proyecto else "obras:lista")

    @property
    def nombre_lista(self):
        return "Proyectos" if self.es_proyecto else "Obras"

    def recalcular_avance(self):
        """Si tiene tareas, el avance sale de ellas: suma de (incidencia × avance de la tarea)."""
        tareas = list(self.tareas.all())
        total = sum((t.incidencia for t in tareas), Decimal(0))
        if not tareas or total <= 0:
            return
        hecho = sum((t.incidencia * t.avance for t in tareas), Decimal(0)) / total
        nuevo = int(hecho.quantize(Decimal(1), rounding=ROUND_HALF_UP))
        if nuevo != self.avance:
            self.avance = nuevo
            self.save(update_fields=["avance", "actualizada"])

    @staticmethod
    def _siguiente_codigo(tipo="obra"):
        prefijo = f"{'PR' if tipo == 'proyecto' else 'OB'}-{date.today().year}-"
        ultimos = Obra.objects.filter(codigo__startswith=prefijo).values_list("codigo", flat=True)
        numeros = [int(c.rsplit("-", 1)[1]) for c in ultimos if c.rsplit("-", 1)[1].isdigit()]
        return f"{prefijo}{(max(numeros, default=0) + 1):03d}"


class AsignacionObra(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="asignaciones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="asignaciones",
                                limit_choices_to={"tipo": "personal", "is_active": True})
    area = models.ForeignKey("cuentas.Area", on_delete=models.PROTECT, related_name="asignaciones")
    funcion = models.CharField("función en la obra", max_length=100, blank=True,
                               help_text="Ej: Director de obra, Proyectista, Compras.")
    es_responsable = models.BooleanField("responsable en la obra", default=False,
                                         help_text="Puede editar los datos de la obra y su equipo.")
    desde = models.DateField(default=date.today)

    class Meta:
        verbose_name = "asignación a obra"
        verbose_name_plural = "asignaciones a obras"
        ordering = ["area__orden", "usuario__first_name"]
        constraints = [
            models.UniqueConstraint(fields=["obra", "usuario", "area"], name="asignacion_unica"),
        ]

    def __str__(self):
        return f"{self.usuario} en {self.obra} ({self.area})"


class Hito(models.Model):
    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="hitos")
    titulo = models.CharField("título", max_length=200)
    fecha = models.DateField()
    completado = models.BooleanField(default=False)
    visible_cliente = models.BooleanField("visible para el cliente", default=True)

    class Meta:
        ordering = ["fecha", "id"]

    def __str__(self):
        return f"{self.titulo} ({self.fecha:%d/%m/%Y})"


class TareaObra(models.Model):
    """Tarea de un proyecto u obra. Su incidencia es cuánto pesa en el avance total (las de una obra suman 100%)."""

    obra = models.ForeignKey(Obra, on_delete=models.CASCADE, related_name="tareas")
    nombre = models.CharField(max_length=200)
    incidencia = models.DecimalField("incidencia (%)", max_digits=5, decimal_places=2,
                                     validators=[MinValueValidator(Decimal("0.01")), MaxValueValidator(100)])
    avance = models.PositiveSmallIntegerField("avance (%)", default=0, validators=[MaxValueValidator(100)])
    orden = models.PositiveIntegerField(default=0)
    actualizada = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "tarea"
        ordering = ["orden", "id"]

    def __str__(self):
        return f"{self.nombre} ({self.incidencia:g}%)"

    @property
    def aporte(self):
        """Puntos que esta tarea suma al avance total."""
        return self.incidencia * self.avance / 100
