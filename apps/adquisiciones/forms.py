from django import forms

from apps.informes.forms import preparar_foto

from .models import Cotizacion, ItemPedido, Pedido, Recepcion

ARCHIVO_MB = 20
FILAS_ITEMS = 25  # filas que trae el formulario; se muestran de a poco con «+ Agregar ítem»


def _tamano(archivo):
    if archivo and archivo.size > ARCHIVO_MB * 1024 * 1024:
        raise forms.ValidationError(f"«{archivo.name}» pesa más de {ARCHIVO_MB} MB.")
    return archivo


class PedidoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = ["obra", "tipo", "titulo", "urgente", "necesario_para", "nota"]
        widgets = {
            "tipo": forms.RadioSelect,
            "necesario_para": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "nota": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {"obra": "Obra o proyecto", "titulo": "Qué se pide (en pocas palabras)", "urgente": "Es urgente"}

    def __init__(self, *args, obras=None, **kwargs):
        super().__init__(*args, **kwargs)
        if obras is not None:
            self.fields["obra"].queryset = obras
        self.fields["obra"].empty_label = "Elegí la obra o el proyecto"
        self.fields["titulo"].widget.attrs["placeholder"] = "Ej.: cemento, cal y arena para la losa"


class ItemForm(forms.ModelForm):
    class Meta:
        model = ItemPedido
        fields = ["descripcion", "cantidad", "unidad"]
        widgets = {
            "descripcion": forms.TextInput(attrs={"placeholder": "Descripción"}),
            "cantidad": forms.NumberInput(attrs={"placeholder": "Cant.", "step": "any", "min": "0"}),
            "unidad": forms.TextInput(attrs={"placeholder": "Unidad", "list": "unidades"}),
        }


ItemsFormSet = forms.inlineformset_factory(Pedido, ItemPedido, form=ItemForm, extra=FILAS_ITEMS, can_delete=True,
                                           max_num=100)


class VariosArchivos(forms.ClearableFileInput):
    allow_multiple_selected = True


class AdjuntosField(forms.FileField):
    widget = VariosArchivos

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({"multiple": True, "accept": "image/*,.pdf,.xlsx,.xls,.doc,.docx"})

    def clean(self, datos, inicial=None):
        archivos = datos if isinstance(datos, (list, tuple)) else ([datos] if datos else [])
        return [_tamano(a) for a in archivos]


class AdjuntosForm(forms.Form):
    adjuntos = AdjuntosField(label="Fotos o archivos (opcional)")


class CotizacionForm(forms.ModelForm):
    class Meta:
        model = Cotizacion
        fields = ["proveedor", "proveedor_nombre", "monto", "detalle", "archivo"]
        widgets = {"monto": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
                   "detalle": forms.TextInput(attrs={"placeholder": "Ej.: entrega en 5 días · pago a 30 días"})}
        labels = {"proveedor": "Proveedor de la Agenda", "proveedor_nombre": "o escribí el nombre",
                  "archivo": "Presupuesto (PDF o foto)"}

    def __init__(self, *args, proveedores=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["proveedor_nombre"].required = False
        self.fields["proveedor"].required = False
        if proveedores is not None:
            self.fields["proveedor"].queryset = proveedores
        self.fields["proveedor"].empty_label = "—"

    def clean_archivo(self):
        return _tamano(self.cleaned_data.get("archivo"))

    def clean(self):
        datos = super().clean()
        if not datos.get("proveedor") and not (datos.get("proveedor_nombre") or "").strip():
            raise forms.ValidationError("Elegí el proveedor de la Agenda o escribí su nombre.")
        if datos.get("proveedor") and not (datos.get("proveedor_nombre") or "").strip():
            datos["proveedor_nombre"] = str(datos["proveedor"])
        return datos


class RecepcionForm(forms.ModelForm):
    completa = forms.TypedChoiceField(label="¿Llegó todo?", coerce=lambda v: v == "si",
                                      choices=[("si", "Sí, llegó todo"), ("no", "Llegó una parte: falta el resto")],
                                      widget=forms.RadioSelect, initial="si")

    class Meta:
        model = Recepcion
        fields = ["completa", "nota", "foto"]
        widgets = {"nota": forms.Textarea(attrs={"rows": 2, "placeholder": "Qué llegó, qué falta, en qué estado"}),
                   "foto": forms.ClearableFileInput(attrs={"accept": "image/*"})}
        labels = {"foto": "Foto del remito (opcional)"}

    def clean_foto(self):
        foto = self.cleaned_data.get("foto")
        return preparar_foto(foto) if foto else foto

    def clean(self):
        datos = super().clean()
        if datos.get("completa") is False and not (datos.get("nota") or "").strip():
            self.add_error("nota", "Contá qué falta.")
        return datos


class FacturaForm(forms.Form):
    factura_numero = forms.CharField(label="Número de factura", max_length=40)
    factura_archivo = forms.FileField(label="Factura (PDF o foto)", required=False)

    def clean_factura_archivo(self):
        return _tamano(self.cleaned_data.get("factura_archivo"))


class EntregaForm(forms.Form):
    fecha_entrega = forms.DateField(label="Fecha de entrega", widget=forms.DateInput(attrs={"type": "date"}))
    entrega_detalle = forms.CharField(label="Quién lo lleva", max_length=150, required=False,
                                      widget=forms.TextInput(attrs={"placeholder": "Ej.: flete del proveedor, 9 h"}))


class ImportarTrelloForm(forms.Form):
    obra = forms.ModelChoiceField(label="Obra", queryset=None, empty_label="Elegí la obra")
    archivo = forms.FileField(label="Archivo exportado de Trello (.json)",
                              widget=forms.ClearableFileInput(attrs={"accept": ".json,application/json"}))

    def __init__(self, *args, obras=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["obra"].queryset = obras

    def clean_archivo(self):
        a = self.cleaned_data["archivo"]
        if a.size > 30 * 1024 * 1024:
            raise forms.ValidationError("El archivo pesa más de 30 MB.")
        return a
