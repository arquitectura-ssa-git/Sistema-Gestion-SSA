from decimal import Decimal

from django import forms
from django.contrib.auth.password_validation import validate_password

from .models import Area, Cliente, MiembroArea, Usuario


class _ConClaveInicial(forms.ModelForm):
    """Alta de usuarios: con contraseña inicial o con invitación por email."""

    clave_inicial = forms.CharField(
        label="Contraseña inicial", required=False, strip=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
        help_text="Dejala vacía para mandarle una invitación por email y que elija su contraseña.",
    )
    enviar_invitacion = forms.BooleanField(
        label="Enviar invitación por email", required=False, initial=True,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True
        if self.instance.pk:
            self.fields["clave_inicial"].label = "Nueva contraseña (opcional)"
            self.fields["clave_inicial"].help_text = "Solo si querés cambiársela."
            self.fields["enviar_invitacion"].initial = False
            self.fields["enviar_invitacion"].label = "Reenviar invitación por email"

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean_clave_inicial(self):
        clave = self.cleaned_data.get("clave_inicial")
        if clave:
            validate_password(clave, self.instance)
        return clave

    def _aplicar_clave(self, usuario):
        clave = self.cleaned_data.get("clave_inicial")
        if clave:
            usuario.set_password(clave)
        elif not usuario.pk:
            usuario.set_unusable_password()


class PersonaForm(_ConClaveInicial):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "cargo", "telefono",
                  "horas_lun", "horas_mar", "horas_mie", "horas_jue", "horas_vie", "is_active"]
        labels = {"first_name": "Nombre", "last_name": "Apellido", "is_active": "Activo (puede ingresar)"}

    DIAS = [("lun", "Lun"), ("mar", "Mar"), ("mie", "Mié"), ("jue", "Jue"), ("vie", "Vie")]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cada día hábil: una casilla "viene" y sus horas. Sin tildar, ese día no tiene horas contratadas.
        for dia, nombre in self.DIAS:
            horas = self.fields[f"horas_{dia}"]
            horas.required = False
            horas.widget.attrs.update({"min": "0.5", "max": "24", "step": "0.5"})
            valor = getattr(self.instance, f"horas_{dia}")
            self.fields[f"viene_{dia}"] = forms.BooleanField(label=nombre, required=False, initial=bool(valor))
            if not valor:
                self.initial[f"horas_{dia}"] = ""
        self.areas = list(Area.objects.all())
        actuales = {}
        if self.instance.pk:
            actuales = {m.area_id: m.rol for m in self.instance.membresias.all()}
        for area in self.areas:
            self.fields[f"area_{area.codigo}"] = forms.ChoiceField(
                label=area.nombre, required=False,
                choices=[("", "No pertenece")] + list(MiembroArea.Rol.choices),
                initial=actuales.get(area.id, ""),
            )
        self.cambios_areas = []

    def campos_areas(self):
        return [self[f"area_{area.codigo}"] for area in self.areas]

    def dias_horas(self):
        return [(self[f"viene_{dia}"], self[f"horas_{dia}"]) for dia, _ in self.DIAS]

    def clean(self):
        datos = super().clean()
        for dia, _ in self.DIAS:
            campo = f"horas_{dia}"
            if not datos.get(f"viene_{dia}"):
                datos[campo] = Decimal(0)
                self.errors.pop(campo, None)
                continue
            horas = datos.get(campo)
            if horas is None:
                if campo not in self.errors:
                    self.add_error(campo, "Poné cuántas horas viene.")
            elif horas <= 0 or horas > 24 or (horas * 2) % 1:
                self.add_error(campo, "Entre 0,5 y 24, en medias horas.")
        if not any(datos.get(f"area_{a.codigo}") for a in self.areas):
            raise forms.ValidationError("Asigná la persona al menos a un área.")
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.tipo = Usuario.Tipo.PERSONAL
        usuario.cliente = None
        self._aplicar_clave(usuario)
        usuario.save()
        self._guardar_areas(usuario)
        return usuario

    def _guardar_areas(self, usuario):
        actuales = {m.area_id: m for m in usuario.membresias.all()}
        for area in self.areas:
            rol = self.cleaned_data.get(f"area_{area.codigo}") or ""
            membresia = actuales.get(area.id)
            if rol and membresia is None:
                MiembroArea.objects.create(usuario=usuario, area=area, rol=rol)
                self.cambios_areas.append(f"+ {area.nombre} ({rol})")
            elif rol and membresia.rol != rol:
                membresia.rol = rol
                membresia.save(update_fields=["rol"])
                self.cambios_areas.append(f"~ {area.nombre} → {rol}")
            elif not rol and membresia is not None:
                membresia.delete()
                self.cambios_areas.append(f"- {area.nombre}")


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ["nombre", "cuit", "email", "telefono", "direccion", "notas"]
        widgets = {"notas": forms.Textarea(attrs={"rows": 3})}


class ContactoClienteForm(_ConClaveInicial):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "email", "telefono", "notif_email", "notif_whatsapp", "is_active"]
        labels = {"first_name": "Nombre", "last_name": "Apellido", "is_active": "Activo (puede ingresar al portal)"}

    def __init__(self, *args, cliente=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.cliente = cliente

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.tipo = Usuario.Tipo.CLIENTE
        if self.cliente is not None:
            usuario.cliente = self.cliente
        self._aplicar_clave(usuario)
        usuario.save()
        return usuario


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["first_name", "last_name", "cargo", "telefono", "notif_email", "notif_whatsapp"]
        labels = {"first_name": "Nombre", "last_name": "Apellido"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.es_cliente:
            del self.fields["cargo"]
