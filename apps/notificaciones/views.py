from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .models import Notificacion


@login_required
def lista(request):
    avisos = list(request.user.notificaciones.all()[:100])
    return render(request, "notificaciones/lista.html", {"avisos": avisos})


@login_required
def ir(request, pk):
    """Marca el aviso como leído y lleva a lo que avisa."""
    n = get_object_or_404(Notificacion, pk=pk, usuario=request.user)
    if not n.leida:
        n.leida = True
        n.save(update_fields=["leida"])
    if n.url and url_has_allowed_host_and_scheme(n.url, allowed_hosts={request.get_host()}):
        return redirect(n.url)
    return redirect("notificaciones:lista")


@login_required
@require_POST
def leer_todas(request):
    request.user.notificaciones.filter(leida=False).update(leida=True)
    return redirect("notificaciones:lista")
