from django.contrib import admin

from .models import Pedido


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "titulo", "obra", "estado", "creado")
    list_filter = ("estado", "tipo")
    search_fields = ("codigo", "titulo")
