from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar

from . import permisos
from .forms import ClienteForm, ContactoClienteForm, PerfilForm, PersonaForm
from .models import Area, Cliente, MiembroArea, Usuario
from .services import enviar_invitacion


def _invitar_si_corresponde(request, form, usuario):
    if form.cleaned_data.get("enviar_invitacion"):
        enviar_invitacion(usuario)
        messages.info(request, f"Se envió la invitación a {usuario.email}.")


# --- Personal --------------------------------------------------------------

# Mismo orden que la escala de grises de las áreas (de Gerencia en negro a Administración en gris claro).
ORDEN_AREAS = [Area.Codigo.GERENCIA, Area.Codigo.GESTION_PROYECTOS, Area.Codigo.DESARROLLO_PROYECTOS,
               Area.Codigo.GESTION_OBRAS, Area.Codigo.DIRECCION_TECNICA, Area.Codigo.GESTION_ADMINISTRATIVA]


def _areas_ordenadas():
    orden = {codigo: i for i, codigo in enumerate(ORDEN_AREAS)}
    return sorted(Area.objects.all(), key=lambda a: orden.get(a.codigo, len(orden)))


@permisos.solo_personal
def areas(request):
    """La vieja página de áreas quedó unificada en Equipo."""
    return redirect("cuentas:personal")


# Orden de la lista de miembros: (título del grupo, regla). Gana la primera regla que se cumple.
_A = Area.Codigo
_GRUPOS_PERSONAL = [
    ("DIR", lambda areas, resp: _A.GERENCIA in areas),
    ("Coordinación", lambda areas, resp: bool(resp & {_A.GESTION_OBRAS, _A.GESTION_PROYECTOS})),
    ("Administración", lambda areas, resp: _A.GESTION_ADMINISTRATIVA in areas),
    ("Área Proyectos", lambda areas, resp: bool(areas & {_A.GESTION_PROYECTOS, _A.DESARROLLO_PROYECTOS})),
    ("Área Obras", lambda areas, resp: bool(areas & {_A.GESTION_OBRAS, _A.DIRECCION_TECNICA})),
    ("Otros", lambda areas, resp: True),
]
# Orden en pantalla (Administración se evalúa antes que las áreas técnicas pero se muestra al final).
_ORDEN_GRUPOS = ["DIR", "Coordinación", "Área Proyectos", "Área Obras", "Administración", "Otros"]


def _grupo_de(persona):
    membresias = list(persona.membresias.all())
    areas = {m.area.codigo for m in membresias}
    resp = {m.area.codigo for m in membresias if m.rol == MiembroArea.Rol.RESPONSABLE}
    return next(titulo for titulo, regla in _GRUPOS_PERSONAL if regla(areas, resp))


@permisos.solo_personal
def personal_lista(request):
    """Equipo: todo el personal agrupado. Lo ve todo el estudio; solo Gerencia agrega y edita."""
    puede_gestionar = permisos.puede_gestionar_personal(request.user)
    personas = Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL).prefetch_related("membresias__area")
    if not (puede_gestionar and request.GET.get("inactivos") == "1"):
        personas = personas.filter(is_active=True)
    grupos = {titulo: [] for titulo in _ORDEN_GRUPOS}
    for p in personas:
        grupos[_grupo_de(p)].append(p)
    secciones = [(titulo, sorted(lista, key=lambda p: (p.first_name.lower(), p.last_name.lower())))
                 for titulo, lista in grupos.items() if lista]
    return render(request, "cuentas/personal_lista.html", {
        "secciones": secciones, "areas": _areas_ordenadas(), "puede_gestionar": puede_gestionar,
    })


@permisos.solo_gerencia
def persona_form(request, pk=None):
    persona = get_object_or_404(Usuario, pk=pk, tipo=Usuario.Tipo.PERSONAL) if pk else None
    form = PersonaForm(request.POST or None, instance=persona)
    if request.method == "POST" and form.is_valid():
        es_alta = persona is None
        persona = form.save()
        if es_alta:
            registrar("personal.alta", f"Alta de personal: {persona.nombre_completo}", objeto=persona,
                      detalle={"areas": form.cambios_areas})
        else:
            registrar("personal.edicion", f"Edición de personal: {persona.nombre_completo}", objeto=persona,
                      detalle={"campos": [c for c in form.changed_data if c != "clave_inicial"],
                               "areas": form.cambios_areas,
                               "cambio_clave": bool(form.cleaned_data.get("clave_inicial"))})
        _invitar_si_corresponde(request, form, persona)
        messages.success(request, f"{persona.nombre_completo} quedó guardado.")
        return redirect("cuentas:personal")
    return render(request, "cuentas/persona_form.html", {"form": form, "persona": persona})


@permisos.solo_personal
@require_POST
def persona_invitar(request, pk):
    persona = get_object_or_404(Usuario, pk=pk)
    if persona.es_cliente:
        _exigir_gestion_clientes(request)
    else:
        permisos.exigir(permisos.puede_gestionar_personal(request.user))
    enviar_invitacion(persona)
    messages.info(request, f"Se envió la invitación a {persona.email}.")
    if persona.es_cliente and persona.cliente_id:
        return redirect("cuentas:cliente", pk=persona.cliente_id)
    return redirect("cuentas:personal")


# --- Clientes --------------------------------------------------------------

def _exigir_gestion_clientes(request):
    permisos.exigir(permisos.puede_gestionar_clientes(request.user))


@permisos.solo_personal
def clientes_lista(request):
    _exigir_gestion_clientes(request)
    q = request.GET.get("q", "").strip()
    clientes = Cliente.objects.prefetch_related("usuarios", "obras")
    if q:
        clientes = clientes.filter(nombre__icontains=q)
    return render(request, "cuentas/clientes_lista.html", {"clientes": clientes, "q": q})


@permisos.solo_personal
def cliente_form(request, pk=None):
    _exigir_gestion_clientes(request)
    cliente = get_object_or_404(Cliente, pk=pk) if pk else None
    form = ClienteForm(request.POST or None, instance=cliente)
    if request.method == "POST" and form.is_valid():
        es_alta = cliente is None
        cliente = form.save()
        registrar(
            "cliente.alta" if es_alta else "cliente.edicion",
            f"{'Alta' if es_alta else 'Edición'} de cliente: {cliente}", objeto=cliente,
            detalle={} if es_alta else {"campos": form.changed_data},
        )
        messages.success(request, f"Cliente {cliente} guardado.")
        return redirect("cuentas:cliente", pk=cliente.pk)
    return render(request, "cuentas/cliente_form.html", {"form": form, "cliente": cliente})


@permisos.solo_personal
def cliente_detalle(request, pk):
    _exigir_gestion_clientes(request)
    cliente = get_object_or_404(Cliente, pk=pk)
    return render(request, "cuentas/cliente_detalle.html", {
        "cliente": cliente,
        "contactos": cliente.usuarios.all(),
        "obras": cliente.obras.all(),
    })


@permisos.solo_personal
def contacto_form(request, cliente_pk, pk=None):
    _exigir_gestion_clientes(request)
    cliente = get_object_or_404(Cliente, pk=cliente_pk)
    contacto = get_object_or_404(Usuario, pk=pk, cliente=cliente) if pk else None
    form = ContactoClienteForm(request.POST or None, instance=contacto, cliente=cliente)
    if request.method == "POST" and form.is_valid():
        es_alta = contacto is None
        contacto = form.save()
        registrar(
            "cliente.contacto_alta" if es_alta else "cliente.contacto_edicion",
            f"{'Alta' if es_alta else 'Edición'} de acceso al portal: {contacto.nombre_completo} ({cliente})",
            objeto=contacto,
        )
        _invitar_si_corresponde(request, form, contacto)
        messages.success(request, f"{contacto.nombre_completo} quedó guardado.")
        return redirect("cuentas:cliente", pk=cliente.pk)
    return render(request, "cuentas/contacto_form.html", {"form": form, "cliente": cliente, "contacto": contacto})


# --- Mi perfil -------------------------------------------------------------

@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        registrar("perfil.edicion", "Actualizó su perfil", objeto=request.user, detalle={"campos": form.changed_data})
        messages.success(request, "Tus datos quedaron guardados.")
        return redirect("cuentas:perfil")
    return render(request, "cuentas/perfil.html", {"form": form})
