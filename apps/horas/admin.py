from django.contrib import admin

from .models import Habilitacion, RegistroHoras


@admin.register(RegistroHoras)
class RegistroHorasAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "obra", "tipo", "horas", "extra")
    list_filter = ("tipo", "extra", "fecha")
    search_fields = ("usuario__email", "usuario__first_name", "obra__nombre", "nota")
    date_hierarchy = "fecha"


@admin.register(Habilitacion)
class HabilitacionAdmin(admin.ModelAdmin):
    list_display = ("fecha", "usuario", "estado", "pedida", "resuelta_por")
    list_filter = ("estado",)
