import json

from django import forms
from django.core.exceptions import ValidationError

from . import arbol
from .models import Plantilla


def leer_estructura(texto, con_avance=False, minimo_una=True):
    """JSON del editor de tareas → datos validados. Lanza ValidationError."""
    try:
        datos = json.loads(texto or "[]")
    except ValueError:
        raise ValidationError("El listado de tareas llegó mal armado. Recargá la página y probá de nuevo.")
    limpio = arbol.validar(datos, con_avance=con_avance)
    if minimo_una and not limpio:
        raise ValidationError("Cargá al menos un rubro.")
    return limpio


class PlantillaForm(forms.ModelForm):
    class Meta:
        model = Plantilla
        fields = ["nombre", "uso", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


class AplicarPlantillaForm(forms.Form):
    plantilla = forms.ModelChoiceField(queryset=Plantilla.objects.none(), label="Plantilla",
                                       empty_label="Elegí una plantilla")

    def __init__(self, *args, tipo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plantilla"].queryset = Plantilla.objects.filter(
            uso__in=[Plantilla.Uso.AMBOS, tipo]).prefetch_related("tareas")
