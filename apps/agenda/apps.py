from django.apps import AppConfig


class AgendaConfig(AppConfig):
    name = "apps.agenda"
    verbose_name = "Agenda de contactos"

    def ready(self):
        from . import sincronizar  # noqa: F401  (Clientes ↔ Agenda)
