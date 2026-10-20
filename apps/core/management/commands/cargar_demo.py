"""Carga datos de demostración: una persona por área, dos clientes, un proyecto, una obra y plantillas de tareas.

Uso:  python manage.py cargar_demo
Todos los usuarios de prueba usan la contraseña CLAVE_DEMO (ver README).
"""

from datetime import date, timedelta

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.auditoria.services import registrar
from apps.cuentas.models import Area, Cliente, MiembroArea, Usuario
from apps.obras.models import AsignacionObra, Hito, Obra, TareaObra
from apps.plantillas.demo import cargar_plantillas_demo

CLAVE_DEMO = "Demo2026!"

A = Area.Codigo
R = MiembroArea.Rol

PERSONAL = [
    # email, nombre, apellido, cargo, área, rol
    ("gerencia@demo.local", "Lucía", "Gómez", "Socia gerente", A.GERENCIA, R.RESPONSABLE),
    ("obras@demo.local", "Juan", "Ruiz", "Jefe de obra", A.GESTION_OBRAS, R.RESPONSABLE),
    ("administracion@demo.local", "Laura", "Sosa", "Administración", A.GESTION_ADMINISTRATIVA, R.RESPONSABLE),
    ("proyectos@demo.local", "Diego", "Paz", "Coordinador de proyectos", A.GESTION_PROYECTOS, R.RESPONSABLE),
    ("desarrollo@demo.local", "Sofía", "Luna", "Proyectista", A.DESARROLLO_PROYECTOS, R.INTEGRANTE),
    ("tecnica@demo.local", "Pablo", "Vera", "Director técnico", A.DIRECCION_TECNICA, R.RESPONSABLE),
]

CLIENTES = [
    # cliente, contacto (email, nombre, apellido, whatsapp)
    ("Familia Pérez", ("cliente@demo.local", "Carlos", "Pérez", "+5491100000001")),
    ("Constructora Sur S.A.", ("cliente2@demo.local", "Ana", "Torres", "+5491100000002")),
]


class Command(BaseCommand):
    help = "Carga usuarios, clientes y obras de demostración."

    @transaction.atomic
    def handle(self, *args, **opciones):
        areas = {a.codigo: a for a in Area.objects.all()}
        personas = {}
        for email, nombre, apellido, cargo, area, rol in PERSONAL:
            usuario, creado = Usuario.objects.get_or_create(
                email=email,
                defaults={"first_name": nombre, "last_name": apellido, "cargo": cargo,
                          "tipo": Usuario.Tipo.PERSONAL, "is_staff": area == A.GERENCIA,
                          "is_superuser": area == A.GERENCIA},
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
                usuario.save()
            MiembroArea.objects.get_or_create(usuario=usuario, area=areas[area], defaults={"rol": rol})
            personas[area] = usuario

        clientes = []
        for nombre_cliente, (email, nombre, apellido, whatsapp) in CLIENTES:
            cliente, _ = Cliente.objects.get_or_create(nombre=nombre_cliente, defaults={"email": email})
            usuario, creado = Usuario.objects.get_or_create(
                email=email,
                defaults={"first_name": nombre, "last_name": apellido, "telefono": whatsapp,
                          "tipo": Usuario.Tipo.CLIENTE, "cliente": cliente},
            )
            if creado:
                usuario.set_password(CLAVE_DEMO)
                usuario.save()
            clientes.append(cliente)

        hoy = date.today()
        casa, creada = Obra.objects.get_or_create(
            nombre="Casa Pérez",
            defaults={"cliente": clientes[0], "direccion": "Los Álamos 123", "localidad": "Pilar",
                      "superficie_m2": 240, "etapa": Obra.Etapa.EJECUCION, "avance": 35,
                      "fecha_inicio": hoy - timedelta(days=120), "fecha_fin_estimada": hoy + timedelta(days=200),
                      "descripcion": "Vivienda unifamiliar de dos plantas con pileta.",
                      "creada_por": personas[A.GERENCIA]},
        )
        if creada:
            equipo = [
                (A.GESTION_OBRAS, "Director de obra", True),
                (A.GESTION_ADMINISTRATIVA, "Compras y pagos", False),
                (A.GESTION_PROYECTOS, "Coordinación", True),
                (A.DESARROLLO_PROYECTOS, "Planos", False),
                (A.DIRECCION_TECNICA, "Visto bueno técnico", False),
            ]
            for area, funcion, responsable in equipo:
                AsignacionObra.objects.create(obra=casa, usuario=personas[area], area=areas[area],
                                              funcion=funcion, es_responsable=responsable)
            for titulo, dias, hecho in [("Fin de excavación", -90, True), ("Estructura planta baja", -20, True),
                                        ("Estructura planta alta", 30, False), ("Cerramientos", 90, False),
                                        ("Entrega de llaves", 200, False)]:
                Hito.objects.create(obra=casa, titulo=titulo, fecha=hoy + timedelta(days=dias), completado=hecho)

        edificio, creada = Obra.objects.get_or_create(
            nombre="Edificio Sur",
            defaults={"cliente": clientes[1], "direccion": "Av. del Sur 850", "localidad": "Avellaneda",
                      "superficie_m2": 3200, "etapa": Obra.Etapa.PROYECTO, "avance": 10,
                      "tipo": Obra.Tipo.PROYECTO,
                      "descripcion": "Edificio de viviendas de 8 pisos.", "creada_por": personas[A.GERENCIA]},
        )
        if creada:
            AsignacionObra.objects.create(obra=edificio, usuario=personas[A.GESTION_PROYECTOS],
                                          area=areas[A.GESTION_PROYECTOS], funcion="Coordinación", es_responsable=True)
            AsignacionObra.objects.create(obra=edificio, usuario=personas[A.DESARROLLO_PROYECTOS],
                                          area=areas[A.DESARROLLO_PROYECTOS], funcion="Anteproyecto")

        plantillas = cargar_plantillas_demo(personas[A.GERENCIA])
        # Tareas con avance: la casa va por la estructura; el edificio, por el anteproyecto.
        for obra, plantilla, avances in [(casa, "Vivienda unifamiliar", [100, 100, 100, 100, 30]),
                                         (edificio, "Proyecto ejecutivo", [100, 25])]:
            if not obra.tareas.exists():
                for n, t in enumerate(plantillas[plantilla].tareas.all()):
                    TareaObra.objects.create(obra=obra, nombre=t.nombre, incidencia=t.incidencia, orden=n,
                                             avance=avances[n] if n < len(avances) else 0)
                obra.recalcular_avance()

        if apps.is_installed("apps.documentos"):
            from apps.documentos.demo import cargar_documentos_demo
            cargar_documentos_demo(casa, personas)
        if apps.is_installed("apps.aprobaciones"):
            from apps.aprobaciones.demo import cargar_solicitudes_demo
            cargar_solicitudes_demo(casa, personas)

        registrar("sistema.demo", "Se cargaron los datos de demostración", usuario=None)
        self.stdout.write(self.style.SUCCESS(
            f"Listo. Usuarios de prueba cargados (contraseña: ver README). Proyecto: {edificio}. Obra: {casa}. "
            f"Plantillas: {', '.join(plantillas)}."
        ))
