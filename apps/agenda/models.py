"""Agenda de contactos del estudio: proveedores, clientes y otros tipos que crea el estudio. Los clientes se
sincronizan con Clientes en los dos sentidos (sincronizar.py); el equipo se muestra desde Equipo."""

from django.db import models

from apps.cuentas.models import nombre_propio


class TipoContacto(models.Model):
    CLIENTE = "cliente"
    PROVEEDOR = "proveedor"

    codigo = models.SlugField(max_length=30, unique=True)
    nombre = models.CharField(max_length=60, unique=True, help_text="Como aparece en el filtro, ej.: Proveedores")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "tipo de contacto"
        verbose_name_plural = "tipos de contacto"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Contacto(models.Model):
    tipo = models.ForeignKey(TipoContacto, on_delete=models.PROTECT, related_name="contactos")
    empresa = models.CharField(max_length=150, blank=True, help_text="Para proveedores o empresas.")
    apellido = models.CharField("apellido", max_length=100, blank=True, help_text="Se guarda en mayúsculas.")
    nombres = models.CharField("nombre", max_length=100, blank=True)
    telefono = models.CharField("teléfono", max_length=40, blank=True)
    email = models.EmailField(blank=True)
    facturacion = models.TextField("datos de facturación", blank=True,
                                   help_text="Razón social, condición frente al IVA, etc.")
    cuit = models.CharField("CUIT / DNI", max_length=20, blank=True)
    domicilio = models.CharField(max_length=200, blank=True)
    cbu = models.CharField("CBU / CVU", max_length=30, blank=True)
    alias = models.CharField(max_length=60, blank=True)
    nota = models.TextField(blank=True)
    cliente = models.OneToOneField("cuentas.Cliente", null=True, blank=True, on_delete=models.CASCADE,
                                   related_name="contacto_agenda")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa", "apellido", "nombres"]

    def __str__(self):
        return self.titulo

    @property
    def persona(self):
        return f"{self.apellido}, {self.nombres}" if self.apellido and self.nombres else self.apellido or self.nombres

    @property
    def titulo(self):
        return self.empresa or self.persona or "(sin nombre)"

    def save(self, *args, **kwargs):
        self.empresa = " ".join(self.empresa.split())
        self.apellido = " ".join(self.apellido.split()).upper()
        self.nombres = nombre_propio(self.nombres)
        super().save(*args, **kwargs)
