from django import forms

from apps.cuentas import permisos
from apps.cuentas.models import Area
from apps.obras.forms import FechaInput

from . import formatos
from .models import Documento

T = Documento.Tipo
A = Documento.Acceso

# Datos propios que se muestran según el tipo de documento.
CAMPOS_POR_TIPO = {
    T.PLANOS: ["numero", "especialidad", "escala"],
    T.PRESUPUESTOS: ["monto", "moneda", "proveedor", "fecha_documento"],
    T.CRONOGRAMAS: ["fecha_documento"],
    T.REPORTES: ["numero", "fecha_documento"],
    T.FOTOS: ["fecha_documento"],
    T.PERMISOS: ["organismo", "numero", "fecha_documento", "vencimiento"],
    T.NORMATIVAS: ["jurisdiccion", "fecha_documento"],
    T.CONTRATOS: ["partes", "fecha_documento", "monto", "moneda"],
}
ETIQUETAS_POR_TIPO = {
    T.PLANOS: {"numero": "N° de plano"},
    T.REPORTES: {"numero": "N° de reporte", "fecha_documento": "Fecha del reporte"},
    T.FOTOS: {"fecha_documento": "Fecha de la foto"},
    T.PERMISOS: {"numero": "N° de expediente", "fecha_documento": "Fecha de otorgamiento"},
    T.NORMATIVAS: {"fecha_documento": "Fecha de publicación"},
    T.CONTRATOS: {"fecha_documento": "Fecha de firma"},
    T.PRESUPUESTOS: {"fecha_documento": "Fecha del presupuesto"},
    T.CRONOGRAMAS: {"fecha_documento": "Fecha de inicio que cubre"},
}
TODOS_LOS_PROPIOS = sorted({c for campos in CAMPOS_POR_TIPO.values() for c in campos})


class VariosArchivosInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class VariosArchivosField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", VariosArchivosInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        limpiar = super().clean
        if isinstance(data, (list, tuple)):
            return [limpiar(d, initial) for d in data]
        return [limpiar(data, initial)]


def _opciones_obra(usuario, campo):
    obras = permisos.obras_del_equipo(usuario).order_by("nombre")
    campo.queryset = obras
    campo.required = False
    campo.empty_label = "Biblioteca general del estudio (sin obra)"
    campo.label_from_instance = lambda o: f"{o.codigo} · {o.nombre}"


def _opciones_acceso(usuario, campo, obra=None, documento=None):
    """El cliente solo aparece para quien puede compartir con él."""
    from apps.obras.models import Obra

    puede = permisos.es_gerencia(usuario)
    if not puede and documento is not None:
        puede = permisos.puede_compartir_con_cliente(usuario, documento)
    elif not puede and isinstance(obra, Obra):
        puede = permisos.es_responsable_de_obra(usuario, obra)
    elif not puede:
        puede = any(permisos.es_responsable_de_obra(usuario, o) for o in permisos.obras_del_equipo(usuario))
    campo.choices = [c for c in A.choices if c[0] != A.CLIENTE or puede]


def _validar_acceso(form, datos, usuario):
    acceso, obra, area = datos.get("acceso"), datos.get("obra"), datos.get("area")
    if acceso == A.CLIENTE:
        if obra is None:
            form.add_error("acceso", "Los documentos de la Biblioteca general no se comparten con clientes.")
        elif not (permisos.es_gerencia(usuario) or permisos.es_responsable_de_obra(usuario, obra)):
            form.add_error("acceso", "Solo los responsables de la obra y Gerencia comparten con el cliente.")
    if acceso == A.RESTRINGIDO and area is None:
        form.add_error("area", "Para restringir un documento elegí su área responsable.")
    if obra is not None and not permisos.puede_subir_documentos(usuario, obra):
        form.add_error("obra", "No estás asignado a esa obra.")


class SubirForm(forms.Form):
    obra = forms.ModelChoiceField(queryset=None)
    tipo = forms.ChoiceField(label="Tipo de documento", choices=T.choices)
    area = forms.ModelChoiceField(label="Área responsable", queryset=Area.objects.all(), required=False)
    acceso = forms.ChoiceField(label="Quién lo ve", choices=A.choices, initial=A.EQUIPO)
    etiquetas = forms.CharField(required=False, max_length=200, help_text="Opcional, separadas por coma.")
    comentario = forms.CharField(label="Comentario", required=False, max_length=300,
                                 help_text="Opcional. Ej: «Entrega para licitación».")
    archivos = VariosArchivosField(label="Archivos")

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        _opciones_obra(usuario, self.fields["obra"])
        _opciones_acceso(usuario, self.fields["acceso"])
        mias = usuario.membresias.select_related("area").first()
        if mias and not self.is_bound:
            self.fields["area"].initial = mias.area_id

    def clean(self):
        datos = super().clean()
        _validar_acceso(self, datos, self.usuario)
        return datos


class DocumentoForm(forms.ModelForm):
    class Meta:
        model = Documento
        fields = ["titulo", "obra", "tipo", "area", "acceso", "etiquetas", "descripcion"] + TODOS_LOS_PROPIOS
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_documento": FechaInput(),
            "vencimiento": FechaInput(),
        }
        labels = {"obra": "Obra", "acceso": "Quién lo ve"}

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        _opciones_obra(usuario, self.fields["obra"])
        _opciones_acceso(usuario, self.fields["acceso"], documento=self.instance)
        tipo = self.instance.tipo
        visibles = set(CAMPOS_POR_TIPO.get(tipo, []))
        for campo in TODOS_LOS_PROPIOS:
            if campo not in visibles:
                del self.fields[campo]
        for campo, texto in ETIQUETAS_POR_TIPO.get(tipo, {}).items():
            if campo in self.fields:
                self.fields[campo].label = texto
        self.campos_propios = [self[c] for c in CAMPOS_POR_TIPO.get(tipo, []) if c in self.fields]

    def clean(self):
        datos = super().clean()
        # El cambio de acceso hacia o desde "cliente" lo decide puede_compartir_con_cliente.
        anterior = self.instance.acceso
        nuevo = datos.get("acceso")
        if A.CLIENTE in (anterior, nuevo) and anterior != nuevo:
            if not permisos.puede_compartir_con_cliente(self.usuario, self.instance) and not permisos.es_gerencia(
                    self.usuario):
                self.add_error("acceso", "Solo los responsables de la obra y Gerencia comparten con el cliente.")
        _validar_acceso(self, datos, self.usuario)
        if datos.get("tipo") and datos["tipo"] != self.instance.tipo and self.instance.versiones.exists():
            version = self.instance.version_actual
            from django.core.files.uploadedfile import SimpleUploadedFile

            error = formatos.validar(datos["tipo"], SimpleUploadedFile(version.nombre_original, b"", None))
            if error:
                self.add_error("tipo", f"El archivo vigente no es compatible con ese tipo. {error}")
        return datos


class VersionForm(forms.Form):
    archivo = forms.FileField(label="Archivo nuevo")
    editable = forms.FileField(label="Archivo editable (opcional)", required=False,
                               help_text="DWG, DXF, RVT, IFC o SKP. Nunca se comparte con el cliente.")
    revision = forms.CharField(label="Revisión", required=False, max_length=10,
                               help_text="Si lo dejás vacío se usa la siguiente letra.")
    comentario = forms.CharField(label="Qué cambió", max_length=300,
                                 help_text="Ej: «Se movió el tabique de la cocina».")

    def __init__(self, *args, documento, **kwargs):
        super().__init__(*args, **kwargs)
        self.documento = documento
        if not documento.es_plano:
            del self.fields["editable"]

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]
        error = formatos.validar(self.documento.tipo, archivo)
        if error:
            raise forms.ValidationError(error)
        return archivo

    def clean_editable(self):
        editable = self.cleaned_data.get("editable")
        if editable:
            error = formatos.validar(self.documento.tipo, editable, editable=True)
            if error:
                raise forms.ValidationError(error)
        return editable

    def clean_revision(self):
        revision = self.cleaned_data["revision"].strip().upper()
        if revision and self.documento.versiones.filter(revision=revision).exists():
            raise forms.ValidationError(f"Ya existe la Rev {revision}.")
        return revision
