from .models import Notificacion


def avisar(usuarios, texto, url="", menos=None):
    """Deja un aviso en la campana de cada persona (una sola vez por persona; nunca a quien hizo la acción)."""
    vistos = set()
    for u in usuarios:
        if u is None or not u.is_active or u.pk in vistos or (menos is not None and u.pk == menos.pk):
            continue
        vistos.add(u.pk)
        Notificacion.objects.create(usuario=u, texto=texto[:300], url=url[:300])
