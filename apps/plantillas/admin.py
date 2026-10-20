from django.contrib import admin

from .models import Plantilla, TareaPlantilla


class TareaInline(admin.TabularInline):
    model = TareaPlantilla
    extra = 0


@admin.register(Plantilla)
class PlantillaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "uso", "actualizada")
    list_filter = ("uso",)
    search_fields = ("nombre",)
    inlines = [TareaInline]
