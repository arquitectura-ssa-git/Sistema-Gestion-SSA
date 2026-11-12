"""Legajos del personal: DNI, título, acuerdo de confidencialidad, contrato o convenio de pasantía y otros
documentos. Solo los ven y gestionan DIR y Asistente de Dirección; los archivos se sirven con permiso."""

import os
import uuid

from django.conf import settings
from django.db import models


def ruta_documento(instancia, nombre):
    extension = os.path.splitext(nombre)[1].lower()[:6] or ".pdf"
    return f"legajos/{instancia.usuario_id}/{uuid.uuid4().hex}{extension}"


class DocumentoLegajo(models.Model):
    class Tipo(models.TextChoices):
        DNI = "dni", "DNI (frente y dorso)"
        TITULO = "titulo", "Título o constancia de alumno regular"
        CONFIDENCIALIDAD = "confidencialidad", "Acuerdo de confidencialidad"
        CONTRATO = "contrato", "Contrato o convenio de pasantía (FAU)"
        OTRO = "otro", "Otro documento"

    OBLIGATORIOS = [Tipo.DNI, Tipo.TITULO, Tipo.CONFIDENCIALIDAD, Tipo.CONTRATO]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="legajo")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    nombre = models.CharField("nombre del documento", max_length=120, blank=True)
    archivo = models.FileField(upload_to=ruta_documento)
    nombre_original = models.CharField(max_length=200, blank=True)
    vence = models.DateField("vence", null=True, blank=True)
    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "documento de legajo"
        verbose_name_plural = "documentos de legajo"
        ordering = ["tipo", "-subido"]

    def __str__(self):
        return f"{self.usuario} · {self.titulo}"

    @property
    def titulo(self):
        return self.nombre if self.tipo == self.Tipo.OTRO and self.nombre else self.get_tipo_display()

    @property
    def es_imagen(self):
        return os.path.splitext(self.archivo.name)[1].lower() in (".jpg", ".jpeg", ".png", ".webp", ".heic")

    @property
    def formato(self):
        return os.path.splitext(self.archivo.name)[1].lower().lstrip(".").upper() or "—"
