from django.contrib import messages
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.auditoria.services import registrar
from apps.cuentas import permisos
from apps.cuentas.models import Usuario

from .forms import ContactoForm, TipoContactoForm
from .models import Contacto, TipoContacto
from .sincronizar import contacto_a_cliente

EQUIPO = "equipo"


def _exigir(request):
    permisos.exigir(permisos.puede_gestionar_agenda(request.user))


@permisos.solo_personal
def lista(request):
    _exigir(request)
    filtro = request.GET.get("tipo", "todos")
    q = request.GET.get("q", "").strip()
    tipos = list(TipoContacto.objects.all())
    contactos = Contacto.objects.select_related("tipo", "cliente")
    equipo = Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL, is_active=True).order_by("last_name", "first_name")
    if q:
        contactos = contactos.filter(Q(empresa__icontains=q) | Q(apellido__icontains=q) | Q(nombres__icontains=q)
                                     | Q(cuit__icontains=q) | Q(email__icontains=q))
        equipo = equipo.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q))
    cant_equipo = Usuario.objects.filter(tipo=Usuario.Tipo.PERSONAL, is_active=True).count()
    fijos = [t for t in tipos if t.codigo in (TipoContacto.PROVEEDOR, TipoContacto.CLIENTE)]
    otros = [t for t in tipos if t not in fijos]
    filtros = ([{"codigo": "todos", "nombre": "Todos", "cantidad": Contacto.objects.count() + cant_equipo}]
               + [{"codigo": t.codigo, "nombre": t.nombre, "cantidad": t.contactos.count()} for t in fijos]
               + [{"codigo": EQUIPO, "nombre": "Equipo", "cantidad": cant_equipo}]
               + [{"codigo": t.codigo, "nombre": t.nombre, "cantidad": t.contactos.count()} for t in otros])
    if filtro not in ("todos", EQUIPO):
        contactos = contactos.filter(tipo__codigo=filtro)
    filas = [] if filtro == EQUIPO else list(contactos)
    personas = list(equipo) if filtro in ("todos", EQUIPO) else []
    elegido = None
    if request.GET.get("c"):
        elegido = Contacto.objects.select_related("tipo", "cliente").filter(pk=request.GET["c"]).first()
    elif filas:
        elegido = filas[0]
    return render(request, "agenda/lista.html", {
        "filtros": filtros, "filtro": filtro, "q": q, "filas": filas, "personas": personas, "elegido": elegido,
    })


@permisos.solo_personal
def contacto_form(request, pk=None):
    _exigir(request)
    contacto = get_object_or_404(Contacto, pk=pk) if pk else None
    inicial = {}
    if not contacto and request.GET.get("tipo"):
        inicial["tipo"] = TipoContacto.objects.filter(codigo=request.GET["tipo"]).first()
    form = ContactoForm(request.POST or None, instance=contacto, initial=inicial)
    if request.method == "POST" and form.is_valid():
        es_alta = contacto is None
        contacto = form.save()
        contacto_a_cliente(contacto)
        registrar("agenda.alta" if es_alta else "agenda.edicion",
                  f"{'Nuevo contacto' if es_alta else 'Contacto editado'} en la Agenda: {contacto} ({contacto.tipo})",
                  objeto=contacto)
        messages.success(request, f"«{contacto}» guardado"
                         + (" y también en Clientes." if contacto.cliente_id else "."))
        return redirect(f"/agenda/?tipo={contacto.tipo.codigo}&c={contacto.pk}")
    return render(request, "agenda/form.html", {"form": form, "contacto": contacto})


@permisos.solo_personal
@require_POST
def eliminar(request, pk):
    _exigir(request)
    contacto = get_object_or_404(Contacto.objects.select_related("cliente"), pk=pk)
    nombre = str(contacto)
    if contacto.cliente_id:
        cliente = contacto.cliente
        if cliente.obras.exists() or cliente.usuarios.exists():
            messages.error(request, f"«{nombre}» es un cliente con proyectos, obras o contactos: no se puede eliminar.")
            return redirect(f"/agenda/?c={contacto.pk}")
        registrar("cliente.baja", f"Se eliminó el cliente (desde la Agenda): {cliente}", objeto=cliente)
        cliente.delete()  # se lleva el contacto
    else:
        contacto.delete()
    registrar("agenda.baja", f"Se eliminó de la Agenda: {nombre}")
    messages.success(request, f"Se eliminó «{nombre}».")
    return redirect("agenda:lista")


@permisos.solo_personal
def tipos(request):
    _exigir(request)
    form = TipoContactoForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        t = form.save(commit=False)
        base = slugify(t.nombre)[:24] or "tipo"
        codigo, n = base, 2
        while codigo in ("todos", EQUIPO) or TipoContacto.objects.filter(codigo=codigo).exists():
            codigo, n = f"{base}-{n}", n + 1
        t.codigo = codigo
        t.orden = (TipoContacto.objects.order_by("-orden").values_list("orden", flat=True).first() or 0) + 1
        t.save()
        registrar("agenda.tipo", f"Nuevo tipo de contacto: {t}")
        messages.success(request, f"Se agregó «{t}».")
        return redirect(f"/agenda/?tipo={t.codigo}")
    return render(request, "agenda/tipos.html", {"form": form, "tipos": TipoContacto.objects.all()})
