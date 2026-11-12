from django.urls import path

from . import views

app_name = "horas"

urlpatterns = [
    path("", views.mio, name="mio"),
    path("repetir/", views.repetir, name="repetir"),
    path("pedir/", views.pedir, name="pedir"),
    path("habilitaciones/", views.habilitaciones, name="habilitaciones"),
    path("habilitaciones/<int:pk>/", views.resolver, name="resolver"),
    path("reportes/", views.reportes, name="reportes"),
    path("feriados/", views.feriados, name="feriados"),
    path("tipos/", views.tipos, name="tipos"),
    path("ausencia/<int:pk>/", views.ausencia, name="ausencia"),
    path("feriados/<int:pk>/", views.feriado_cambiar, name="feriado_cambiar"),
]
