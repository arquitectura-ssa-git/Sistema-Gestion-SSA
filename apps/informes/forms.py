from io import BytesIO

from django import forms
from django.core.files.base import ContentFile

from .models import Gremio, HabilitacionInforme, InformeDiario

FOTO_MAX = 1600  # px del lado más largo: alcanza para ver detalles y no llena el servidor
FOTO_MB = 25


def preparar_foto(archivo):
    """Achica la foto (hasta 1600 px) y la guarda como JPG liviano, derecha aunque venga girada del celular."""
    from PIL import Image, ImageOps

    try:
        from pillow_heif import register_heif_opener

        register_heif_opener()  # fotos de iPhone
    except ImportError:
        pass
    try:
        imagen = ImageOps.exif_transpose(Image.open(archivo)).convert("RGB")
        imagen.thumbnail((FOTO_MAX, FOTO_MAX), Image.LANCZOS)
    except Exception:
        raise forms.ValidationError(f"No se pudo leer «{archivo.name}». Probá con una foto JPG o PNG.")
    salida = BytesIO()
    imagen.save(salida, "JPEG", quality=80, optimize=True)
    return ContentFile(salida.getvalue(), name="foto.jpg")


class VariasFotos(forms.ClearableFileInput):
    allow_multiple_selected = True


class CampoFotos(forms.FileField):
    widget = VariasFotos

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)
        self.widget.attrs.update({"accept": "image/*", "multiple": True})

    def clean(self, datos, inicial=None):
        archivos = datos if isinstance(datos, (list, tuple)) else ([datos] if datos else [])
        listas = []
        for a in archivos:
            if a.size > FOTO_MB * 1024 * 1024:
                raise forms.ValidationError(f"«{a.name}» pesa más de {FOTO_MB} MB.")
            listas.append(preparar_foto(a))
        return listas


class InformeForm(forms.ModelForm):
    fotos_nuevas = CampoFotos(label="Fotos de las tareas en ejecución")
    fotos_libro = CampoFotos(label="Foto de la hoja del libro de obra")

    class Meta:
        model = InformeDiario
        fields = ["clima", "se_trabajo", "motivo_sin_trabajo", "notas_pedido", "observaciones"]
        widgets = {
            "clima": forms.RadioSelect,
            "notas_pedido": forms.Textarea(attrs={"rows": 3, "placeholder": "Lo que quedó asentado en el libro de obra"}),
            "observaciones": forms.Textarea(attrs={"rows": 3}),
            "motivo_sin_trabajo": forms.TextInput(attrs={"placeholder": "Ej.: lluvia intensa, terreno anegado"}),
        }

    def __init__(self, *args, fotos_actuales=0, **kwargs):
        super().__init__(*args, **kwargs)
        self.fotos_actuales = fotos_actuales
        self.gremios = list(Gremio.objects.filter(activo=True))
        actuales = {p.gremio_id: p.cantidad for p in self.instance.personal.all()} if self.instance.pk else {}
        for g in self.gremios:
            self.fields[f"gremio_{g.pk}"] = forms.IntegerField(
                label=g.nombre, required=False, min_value=0, max_value=500, initial=actuales.get(g.pk),
                widget=forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "0"}))

    def campos_gremios(self):
        return [self[f"gremio_{g.pk}"] for g in self.gremios]

    def clean(self):
        datos = super().clean()
        if datos.get("clima") != InformeDiario.Clima.LLUVIA:
            datos["se_trabajo"] = True  # con sol se trabaja; la pregunta es solo para los días de lluvia
        if datos.get("se_trabajo"):
            datos["motivo_sin_trabajo"] = ""
        from .reglas import MAX_FOTOS

        nuevas = len(datos.get("fotos_nuevas") or []) + len(datos.get("fotos_libro") or [])
        if self.fotos_actuales + nuevas > MAX_FOTOS:
            raise forms.ValidationError(f"Cada informe admite hasta {MAX_FOTOS} fotos "
                                        f"(ya tiene {self.fotos_actuales}).")
        return datos

    def personal(self):
        """{gremio: cantidad} con lo que se cargó (sin los vacíos ni los ceros)."""
        return {g: self.cleaned_data.get(f"gremio_{g.pk}") for g in self.gremios
                if self.cleaned_data.get(f"gremio_{g.pk}")}


class PedidoCorreccionForm(forms.ModelForm):
    class Meta:
        model = HabilitacionInforme
        fields = ["motivo"]
        widgets = {"motivo": forms.TextInput(attrs={"placeholder": "Qué hay que cargar o corregir"})}


class GremioForm(forms.ModelForm):
    class Meta:
        model = Gremio
        fields = ["nombre"]
        widgets = {"nombre": forms.TextInput(attrs={"placeholder": "Ej.: Vidrieros"})}
