from decimal import Decimal

from django import forms
from django.forms import BaseModelFormSet, modelformset_factory

from apps.obras.models import Obra

from . import reglas
from .models import Feriado, Habilitacion, RegistroHoras


class RegistroForm(forms.ModelForm):
    class Meta:
        model = RegistroHoras
        fields = ["obra", "tipo", "horas", "extra", "nota"]
        widgets = {
            "horas": forms.NumberInput(attrs={"min": "0.5", "max": "24", "step": "0.5", "inputmode": "decimal"}),
            "nota": forms.TextInput(attrs={"placeholder": "Opcional"}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Todos los proyectos y obras activos (se puede colaborar en uno sin estar en el equipo); si una carga
        # ya usaba uno que después se pausó o finalizó, se mantiene.
        activas = Obra.objects.filter(estado=Obra.Estado.ACTIVA)
        if self.instance.pk and self.instance.obra_id:
            activas = Obra.objects.filter(pk=self.instance.obra_id) | activas
        campo = self.fields["obra"]
        campo.queryset = activas.distinct().order_by("tipo", "nombre")
        campo.required = False
        etiqueta = lambda o: f"{o.nombre} · {o.get_tipo_display()}"  # noqa: E731
        campo.label_from_instance = etiqueta
        # Arriba, en su propio grupo, los proyectos y obras donde la persona está en el equipo.
        mias = set(usuario.asignaciones.values_list("obra_id", flat=True)) if usuario else set()
        obras = list(campo.queryset)
        propias = [(o.pk, etiqueta(o)) for o in obras if o.pk in mias]
        resto = [(o.pk, etiqueta(o)) for o in obras if o.pk not in mias]
        opciones = [("", "Estudio / sin proyecto")]
        if propias:
            opciones += [("Tus proyectos y obras", propias), ("Los demás", resto)]
        else:
            opciones += resto
        campo.choices = opciones

    def clean_horas(self):
        horas = self.cleaned_data.get("horas")
        if horas is not None and not reglas.es_media_hora(horas):
            raise forms.ValidationError("Cargá las horas de a media hora (0,5).")
        return horas


class BaseDiaFormSet(BaseModelFormSet):
    """Todas las cargas de una persona en un día. Valida que las horas normales no pasen las contratadas."""

    def __init__(self, *args, usuario, fecha, **kwargs):
        self.usuario, self.fecha = usuario, fecha
        kwargs.setdefault("queryset", RegistroHoras.objects.filter(usuario=usuario, fecha=fecha).select_related("obra"))
        super().__init__(*args, **kwargs)

    def get_form_kwargs(self, index):
        return {**super().get_form_kwargs(index), "usuario": self.usuario}

    def vigentes(self):
        return [f for f in self.forms
                if hasattr(f, "cleaned_data") and f.cleaned_data and not self._should_delete_form(f)]

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        normales = sum((f.cleaned_data["horas"] for f in self.vigentes() if not f.cleaned_data.get("extra")), Decimal(0))
        extras = sum((f.cleaned_data["horas"] for f in self.vigentes() if f.cleaned_data.get("extra")), Decimal(0))
        contratadas = reglas.horas_contratadas(self.usuario, self.fecha)
        if normales > contratadas:
            if contratadas:
                raise forms.ValidationError(
                    f"Cargaste {normales:g} h normales y tu jornada es de {contratadas:g} h. "
                    f"Marcá las {normales - contratadas:g} h que sobran como hora extra.")
            dia_feriado = reglas.feriado(self.fecha)
            if dia_feriado:
                raise forms.ValidationError(
                    f"Hoy es feriado ({dia_feriado.nombre}): tu jornada se computa sola y lo que cargues va como extra.")
            raise forms.ValidationError("Los sábados y domingos todas las horas se cargan como extra.")
        if normales + extras > 24:
            raise forms.ValidationError("Un día no puede tener más de 24 horas.")

    def save(self, commit=True):
        for f in self.deleted_forms:
            if f.instance.pk:
                f.instance.delete()
        guardados = []
        for f in self.vigentes():
            obj = f.save(commit=False)
            obj.usuario, obj.fecha = self.usuario, self.fecha
            obj.save()
            guardados.append(obj)
        return guardados


DiaFormSet = modelformset_factory(RegistroHoras, form=RegistroForm, formset=BaseDiaFormSet, extra=3, can_delete=True)


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Habilitacion
        fields = ["motivo"]
        widgets = {"motivo": forms.TextInput(attrs={"placeholder": "Ej: estuve en obra todo el día y no pude cargar"})}


class FiltroReporteForm(forms.Form):
    AGRUPAR = [("obra", "Por proyecto u obra"), ("persona", "Por persona"), ("tipo", "Por tipo de tarea")]
    desde = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    hasta = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    agrupar = forms.ChoiceField(choices=AGRUPAR, initial="obra")

    def clean(self):
        datos = super().clean()
        if datos.get("desde") and datos.get("hasta") and datos["hasta"] < datos["desde"]:
            self.add_error("hasta", "La fecha final no puede ser anterior a la inicial.")
        return datos


class FeriadoForm(forms.ModelForm):
    class Meta:
        model = Feriado
        fields = ["fecha", "nombre", "tipo", "aplica"]
        widgets = {"fecha": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}
