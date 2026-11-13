"""Avisos dentro de SOPHIA: la campana de arriba muestra cuántos hay sin leer. Más adelante también salen por email
o WhatsApp."""

from django.conf import settings
from django.db import models


class Notificacion(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notificaciones")
    texto = models.CharField(max_length=300)
    url = models.CharField(max_length=300, blank=True)
    leida = models.BooleanField(default=False)
    creada = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-creada"]
        indexes = [models.Index(fields=["usuario", "leida"])]

    def __str__(self):
        return self.texto
