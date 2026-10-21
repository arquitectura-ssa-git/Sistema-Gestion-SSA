from django import forms

from apps.cuentas.models import Area, MiembroArea, Usuario
from apps.plantillas.models import Plantilla

from .models import AsignacionObra, Hito, Obra


class FechaInput(forms.DateInput):
    input_type = "date"

    def __init__(self, **kwargs):
        super().__init__(format="%Y-%m-%d", **kwargs)


class ObraForm(forms.ModelForm):
    class Meta:
        model = Obra
        fields = ["tipo", "codigo", "nombre", "cliente", "direccion", "localidad", "superficie_m2", "descripcion",
                  "etapa", "estado", "fecha_inicio", "fecha_fin_estimada", "avance"]
        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
            "fecha_inicio": FechaInput(),
            "fecha_fin_estimada": FechaInput(),
            "avance": forms.NumberInput(attrs={"min": 0, "max": 100, "step": 1}),
        }

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tipo"].widget = forms.RadioSelect(choices=Obra.Tipo.choices)
        self.fields["tipo"].help_text = ("Proyecto: trabajo de diseño, planos o trámites. "
                                         "Obra: construcción en ejecución.")
        self.fields["cliente"].empty_label = "Sin cliente por ahora"
        if not self.instance.pk:
            # Solo al crear: se copian sus tareas y después se ajustan para este proyecto u obra.
            self.fields["plantilla"] = forms.ModelChoiceField(
                queryset=Plantilla.objects.all(), required=False, label="Plantilla de tareas",
                empty_label="Sin plantilla (cargar las tareas después)",
                help_text="Se copian sus etapas, rubros e ítems; después los ajustás para este proyecto.")
            self.fields["plantilla"].label_from_instance = lambda p: f"{p.nombre} · {p.get_uso_display()}"
            if usuario is not None:
                from apps.cuentas import permisos

                con_tareas = permisos.obras_visibles(usuario).filter(tareas__isnull=False).distinct().order_by("nombre")
                self.fields["copiar_de"] = forms.ModelChoiceField(
                    queryset=con_tareas, required=False, label="O copiar las tareas de un proyecto u obra",
                    empty_label="No copiar",
                    help_text="Toma las etapas, rubros e ítems tal como quedaron ajustados (con el avance en 0).")
                self.fields["copiar_de"].label_from_instance = lambda o: f"{o.nombre} · {o.codigo}"
        if self.instance.pk and self.instance.tareas.exists():
            self.fields["avance"].disabled = True
            self.fields["avance"].help_text = "Se calcula solo con el avance de las tareas (pestaña Tareas)."

    def clean_codigo(self):
        return self.cleaned_data["codigo"].strip().upper()

    def clean(self):
        datos = super().clean()
        plantilla, tipo = datos.get("plantilla"), datos.get("tipo")
        if plantilla and datos.get("copiar_de"):
            self.add_error("copiar_de", "Elegí una plantilla o un proyecto para copiar, no los dos.")
        if plantilla and tipo and not plantilla.sirve_para(tipo):
            self.add_error("plantilla", f"«{plantilla}» es una plantilla para {plantilla.get_uso_display().lower()}.")
        inicio, fin = datos.get("fecha_inicio"), datos.get("fecha_fin_estimada")
        if inicio and fin and fin < inicio:
            self.add_error("fecha_fin_estimada", "El fin estimado no puede ser anterior al inicio.")
        return datos


class AsignacionForm(forms.ModelForm):
    class Meta:
        model = AsignacionObra
        fields = ["usuario", "area", "funcion", "es_responsable"]
        labels = {"usuario": "Persona", "area": "Área"}

    def __init__(self, *args, obra, **kwargs):
        super().__init__(*args, **kwargs)
        self.obra = obra
        self.fields["usuario"].queryset = Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL, is_active=True)
        self.fields["usuario"].label_from_instance = lambda u: f"{u.nombre_completo}" + (f" · {u.cargo}" if u.cargo else "")
        self.fields["area"].queryset = Area.objects.all()

    def clean(self):
        datos = super().clean()
        usuario, area = datos.get("usuario"), datos.get("area")
        if usuario and area:
            if not MiembroArea.objects.filter(usuario=usuario, area=area).exists():
                self.add_error("area", f"{usuario.nombre_completo} no pertenece a {area.nombre}. "
                                       "Asignale esa área en Personal o elegí otra.")
            elif AsignacionObra.objects.filter(obra=self.obra, usuario=usuario, area=area).exists():
                self.add_error("usuario", f"{usuario.nombre_completo} ya está en esta obra por {area.nombre}.")
        return datos

    def save(self, commit=True):
        asignacion = super().save(commit=False)
        asignacion.obra = self.obra
        if commit:
            asignacion.save()
        return asignacion


class HitoForm(forms.ModelForm):
    class Meta:
        model = Hito
        fields = ["titulo", "fecha", "visible_cliente"]
        widgets = {"fecha": FechaInput()}


class DuplicarObraForm(forms.Form):
    nombre = forms.CharField(max_length=200)
    cliente = forms.ModelChoiceField(queryset=None, required=False, empty_label="Sin cliente por ahora")
    copiar_equipo = forms.BooleanField(label="Copiar el equipo (personas, áreas y responsables)", required=False,
                                       initial=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.cuentas.models import Cliente

        self.fields["cliente"].queryset = Cliente.objects.all()


class GuardarPlantillaForm(forms.Form):
    nombre = forms.CharField(label="Nombre de la plantilla", max_length=150)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip()
        if Plantilla.objects.filter(nombre__iexact=nombre).exists():
            raise forms.ValidationError("Ya hay una plantilla con ese nombre.")
        return nombre
