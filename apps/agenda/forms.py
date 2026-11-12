from django import forms

from .models import Contacto, TipoContacto


class ContactoForm(forms.ModelForm):
    class Meta:
        model = Contacto
        fields = ["tipo", "empresa", "apellido", "nombres", "telefono", "email", "cuit", "domicilio", "facturacion",
                  "cbu", "alias", "nota"]
        widgets = {
            "apellido": forms.TextInput(attrs={"class": "en-mayusculas"}),
            "nombres": forms.TextInput(attrs={"class": "nombre-propio"}),
            "facturacion": forms.Textarea(attrs={"rows": 2}),
            "nota": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].empty_label = None
        self.fields["tipo"].label = "Tipo de contacto"

    def clean(self):
        datos = super().clean()
        if not (datos.get("empresa") or datos.get("apellido") or datos.get("nombres")):
            raise forms.ValidationError("Poné la empresa o el apellido y nombre del contacto.")
        return datos


class TipoContactoForm(forms.ModelForm):
    class Meta:
        model = TipoContacto
        fields = ["nombre"]
        widgets = {"nombre": forms.TextInput(attrs={"placeholder": "Ej.: Organismos, Profesionales"})}
