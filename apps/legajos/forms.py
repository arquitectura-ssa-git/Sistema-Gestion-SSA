import os

from django import forms

from .models import DocumentoLegajo

EXTENSIONES = (".pdf", ".jpg", ".jpeg", ".png", ".webp", ".heic")
MAX_MB = 20


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = DocumentoLegajo
        fields = ["tipo", "nombre", "archivo", "vence"]
        widgets = {"tipo": forms.HiddenInput(), "vence": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
                   "nombre": forms.TextInput(attrs={"placeholder": "Ej.: CV, seguro, alta en AFIP"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["archivo"].widget.attrs["accept"] = ",".join(EXTENSIONES) + ",image/*"
        self.fields["archivo"].label = "Foto o PDF"

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        if os.path.splitext(archivo.name)[1].lower() not in EXTENSIONES:
            raise forms.ValidationError("Subí un PDF o una foto (JPG, PNG, HEIC).")
        if archivo.size > MAX_MB * 1024 * 1024:
            raise forms.ValidationError(f"El archivo pesa más de {MAX_MB} MB.")
        return archivo

    def clean(self):
        datos = super().clean()
        if datos.get("tipo") == DocumentoLegajo.Tipo.OTRO and not datos.get("nombre"):
            self.add_error("nombre", "Poné qué documento es.")
        return datos
