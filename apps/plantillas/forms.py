from decimal import Decimal

from django import forms
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Plantilla, TareaPlantilla

TOTAL = Decimal(100)
TOLERANCIA = Decimal("0.01")


class BaseTareasFormSet(BaseInlineFormSet):
    """Filas de tareas con incidencia: las que quedan tienen que sumar 100%.

    El orden de las tareas es el de las filas en pantalla.
    """

    minimo_una = True

    def formularios_vigentes(self):
        return [f for f in self.forms
                if f.has_changed() or f.instance.pk
                if not (self.can_delete and self._should_delete_form(f))]

    def total_incidencia(self):
        return sum((f.cleaned_data.get("incidencia") or 0 for f in self.formularios_vigentes()
                    if hasattr(f, "cleaned_data")), Decimal(0))

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        vigentes = self.formularios_vigentes()
        if not vigentes:
            if self.minimo_una:
                raise forms.ValidationError("Cargá al menos una tarea.")
            return
        total = self.total_incidencia()
        if abs(total - TOTAL) > TOLERANCIA:
            raise forms.ValidationError(
                f"Las incidencias suman {total:g}%. Tienen que sumar 100% para que el avance sea correcto.")

    def save(self, commit=True):
        for f in self.deleted_forms:
            if f.instance.pk:
                f.instance.delete()
        guardadas = []
        for orden, f in enumerate(self.formularios_vigentes()):
            obj = f.save(commit=False)
            setattr(obj, self.fk.name, self.instance)
            obj.orden = orden
            obj.save()
            guardadas.append(obj)
        return guardadas


def widgets_tarea():
    return {
        "nombre": forms.TextInput(attrs={"placeholder": "Ej: Estructura de hormigón"}),
        "incidencia": forms.NumberInput(attrs={"min": "0.01", "max": "100", "step": "0.01", "data-incidencia": ""}),
    }


class PlantillaForm(forms.ModelForm):
    class Meta:
        model = Plantilla
        fields = ["nombre", "uso", "descripcion"]
        widgets = {"descripcion": forms.Textarea(attrs={"rows": 2})}


TareasPlantillaFormSet = inlineformset_factory(
    Plantilla, TareaPlantilla, formset=BaseTareasFormSet, fields=["nombre", "incidencia"],
    widgets=widgets_tarea(), extra=0, can_delete=True,
)


class AplicarPlantillaForm(forms.Form):
    plantilla = forms.ModelChoiceField(queryset=Plantilla.objects.none(), label="Plantilla",
                                       empty_label="Elegí una plantilla")

    def __init__(self, *args, tipo, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["plantilla"].queryset = Plantilla.objects.filter(
            uso__in=[Plantilla.Uso.AMBOS, tipo]).prefetch_related("tareas")
