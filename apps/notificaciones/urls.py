from django.urls import path

from . import views

app_name = "notificaciones"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("<int:pk>/", views.ir, name="ir"),
    path("leer-todas/", views.leer_todas, name="leer_todas"),
]
