from datetime import date
from decimal import Decimal

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El email es obligatorio.")
        usuario = self.model(email=self.normalize_email(email).lower(), **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("tipo", Usuario.Tipo.PERSONAL)
        return self._crear(email, password, **extra)


class Cliente(models.Model):
    """Persona o empresa dueña de una o más obras.

    Puede tener varios contactos con acceso al portal (Usuario.cliente).
    """

    nombre = models.CharField("nombre o razón social", max_length=200)
    cuit = models.CharField("CUIT / DNI", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    notas = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    class Tipo(models.TextChoices):
        PERSONAL = "personal", "Personal del estudio"
        CLIENTE = "cliente", "Cliente"

    username = None
    email = models.EmailField("email", unique=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices, default=Tipo.PERSONAL)
    cargo = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(
        "WhatsApp", max_length=30, blank=True,
        help_text="Con código de país, ej: +5491122334455",
    )
    cliente = models.ForeignKey(
        Cliente, null=True, blank=True, on_delete=models.PROTECT, related_name="usuarios",
        help_text="Solo para usuarios de tipo cliente.",
    )
    # Horas contratadas de cada día hábil (0 = ese día no viene). En Time Report, lo que pase de esto es extra.
    horas_lun = models.DecimalField("lunes", max_digits=3, decimal_places=1, default=8)
    horas_mar = models.DecimalField("martes", max_digits=3, decimal_places=1, default=8)
    horas_mie = models.DecimalField("miércoles", max_digits=3, decimal_places=1, default=8)
    horas_jue = models.DecimalField("jueves", max_digits=3, decimal_places=1, default=8)
    horas_vie = models.DecimalField("viernes", max_digits=3, decimal_places=1, default=8)
    notif_email = models.BooleanField("recibir avisos por email", default=True)
    notif_whatsapp = models.BooleanField("recibir avisos por WhatsApp", default=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        ordering = ["first_name", "last_name", "email"]

    def __str__(self):
        return self.nombre_completo

    DIAS_HABILES = ["lun", "mar", "mie", "jue", "vie"]

    def horas_del_dia(self, fecha):
        """Horas contratadas para ese día de la semana (0 los sábados y domingos)."""
        if fecha.weekday() >= 5:
            return Decimal(0)
        return Decimal(getattr(self, f"horas_{self.DIAS_HABILES[fecha.weekday()]}") or 0)

    @property
    def horas_semanales(self):
        return sum((Decimal(getattr(self, f"horas_{d}") or 0) for d in self.DIAS_HABILES), Decimal(0))

    @property
    def nombre_completo(self):
        return self.get_full_name() or self.email

    @property
    def es_cliente(self):
        return self.tipo == self.Tipo.CLIENTE

    @property
    def es_personal(self):
        return self.tipo == self.Tipo.PERSONAL


class Area(models.Model):
    class Codigo(models.TextChoices):
        GERENCIA = "gerencia", "Gerencia"
        GESTION_OBRAS = "gestion_obras", "Gestión de Obras"
        GESTION_ADMINISTRATIVA = "gestion_administrativa", "Gestión Administrativa"
        GESTION_PROYECTOS = "gestion_proyectos", "Gestión de Proyectos"
        DESARROLLO_PROYECTOS = "desarrollo_proyectos", "Desarrollo de Proyectos"
        DIRECCION_TECNICA = "direccion_tecnica", "Dirección Técnica"

    codigo = models.CharField(max_length=40, unique=True, choices=Codigo.choices)
    nombre = models.CharField(max_length=80)
    descripcion = models.TextField("descripción", blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    miembros = models.ManyToManyField(Usuario, through="MiembroArea", related_name="areas")

    class Meta:
        verbose_name = "área"
        ordering = ["orden"]

    def __str__(self):
        return self.nombre


class MiembroArea(models.Model):
    class Rol(models.TextChoices):
        RESPONSABLE = "responsable", "Responsable"
        INTEGRANTE = "integrante", "Integrante"

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="membresias")
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name="membresias")
    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.INTEGRANTE)
    desde = models.DateField(default=date.today)

    class Meta:
        verbose_name = "miembro de área"
        verbose_name_plural = "miembros de áreas"
        constraints = [models.UniqueConstraint(fields=["usuario", "area"], name="miembro_unico_por_area")]

    def __str__(self):
        return f"{self.usuario} · {self.area} ({self.get_rol_display()})"
