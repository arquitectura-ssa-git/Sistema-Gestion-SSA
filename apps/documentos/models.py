import os
import uuid

from django.conf import settings
from django.db import models
from django.utils.functional import cached_property


class Documento(models.Model):
    class Tipo(models.TextChoices):
        PLANOS = "planos", "Planos"
        PLANILLAS = "planillas", "Planillas"
        PRESUPUESTOS = "presupuestos", "Presupuestos"
        CRONOGRAMAS = "cronogramas", "Cronogramas"
        REPORTES = "reportes", "Reportes de obra"
        FOTOS = "fotos", "Fotos de obra"
        PERMISOS = "permisos", "Permisos y trámites"
        NORMATIVAS = "normativas", "Normativas"
        CONTRATOS = "contratos", "Contratos"
        OTROS = "otros", "Otros"

    class Acceso(models.TextChoices):
        EQUIPO = "equipo", "Equipo de la obra"
        RESTRINGIDO = "restringido", "Restringido"
        CLIENTE = "cliente", "Compartido con el cliente"

    class EstadoPlano(models.TextChoices):
        ELABORACION = "elaboracion", "En elaboración"
        REVISION = "revision", "Para revisión"
        APROBADO = "aprobado", "Aprobado para obra"

    class Especialidad(models.TextChoices):
        ARQUITECTURA = "arquitectura", "Arquitectura"
        ESTRUCTURA = "estructura", "Estructura"
        SANITARIA = "sanitaria", "Sanitaria"
        ELECTRICA = "electrica", "Eléctrica"
        GAS = "gas", "Gas"
        DETALLES = "detalles", "Detalles"
        OTRA = "otra", "Otra"

    obra = models.ForeignKey("obras.Obra", null=True, blank=True, on_delete=models.PROTECT,
                             related_name="documentos", help_text="Vacío = Biblioteca general del estudio.")
    tipo = models.CharField(max_length=20, choices=Tipo.choices)
    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    etiquetas = models.CharField(max_length=200, blank=True, help_text="Separadas por coma.")
    area = models.ForeignKey("cuentas.Area", null=True, blank=True, on_delete=models.SET_NULL,
                             related_name="documentos", verbose_name="área responsable")
    acceso = models.CharField("nivel de acceso", max_length=12, choices=Acceso.choices, default=Acceso.EQUIPO)

    # Datos propios de cada tipo (los que no aplican quedan vacíos).
    numero = models.CharField("número", max_length=40, blank=True,
                              help_text="N° de plano (A-101), de expediente o de reporte.")
    especialidad = models.CharField(max_length=20, choices=Especialidad.choices, blank=True)
    escala = models.CharField(max_length=20, blank=True, help_text="Ej: 1:50")
    estado_plano = models.CharField("estado del plano", max_length=12, choices=EstadoPlano.choices, blank=True)
    organismo = models.CharField(max_length=120, blank=True, help_text="Municipio, colegio, empresa de servicios…")
    fecha_documento = models.DateField("fecha", null=True, blank=True,
                                       help_text="De la foto, del reporte, de otorgamiento o de firma.")
    vencimiento = models.DateField(null=True, blank=True)
    monto = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    moneda = models.CharField(max_length=3, blank=True, choices=[("ARS", "ARS"), ("USD", "USD")])
    proveedor = models.CharField(max_length=120, blank=True)
    partes = models.CharField(max_length=200, blank=True)
    jurisdiccion = models.CharField("jurisdicción", max_length=120, blank=True)

    archivado = models.BooleanField(default=False)
    en_papelera = models.BooleanField(default=False)
    papelera_en = models.DateTimeField(null=True, blank=True)
    papelera_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="documentos_subidos")
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-actualizado"]
        indexes = [models.Index(fields=["obra", "tipo"]), models.Index(fields=["numero"])]

    def __str__(self):
        if self.tipo == self.Tipo.PLANOS and self.numero:
            return f"{self.numero} {self.titulo}"
        return self.titulo

    @cached_property
    def version_actual(self):
        versiones = getattr(self, "_versiones_prefetch", None)
        if versiones is not None:
            return versiones[0] if versiones else None
        return self.versiones.order_by("-numero").first()

    @property
    def es_plano(self):
        return self.tipo == self.Tipo.PLANOS

    @property
    def lista_etiquetas(self):
        return [e.strip() for e in self.etiquetas.split(",") if e.strip()]

    def version_para_cliente(self):
        """Lo que ve el cliente: en planos, la última revisión aprobada para obra; si no hay, la última."""
        if self.es_plano:
            aprobada = self.versiones.filter(aprobada_en__isnull=False).order_by("-numero").first()
            if aprobada:
                return aprobada
        return self.version_actual

    def version_para_obra(self):
        if not self.es_plano:
            return self.version_actual
        return self.versiones.filter(aprobada_en__isnull=False).order_by("-numero").first()


def _carpeta(documento):
    if documento.obra_id:
        return f"obras/{documento.obra.codigo or documento.obra_id}/{documento.tipo}"
    return f"biblioteca/{documento.tipo}"


def ruta_archivo(version, nombre):
    extension = os.path.splitext(nombre)[1].lower()[:10]
    return f"{_carpeta(version.documento)}/{uuid.uuid4().hex}{extension}"


def ruta_derivado(version, nombre):
    return f"{_carpeta(version.documento)}/derivados/{uuid.uuid4().hex}.jpg"


class VersionDocumento(models.Model):
    documento = models.ForeignKey(Documento, on_delete=models.CASCADE, related_name="versiones")
    numero = models.PositiveIntegerField()
    revision = models.CharField("revisión", max_length=10, help_text="A, B, C…")
    comentario = models.CharField("qué cambió", max_length=300, blank=True)

    archivo = models.FileField(upload_to=ruta_archivo, max_length=300, blank=True)
    # En lugar de un archivo subido, la versión puede ser un enlace de Google Drive (no se duplica nada).
    enlace = models.URLField("enlace de Drive", max_length=500, blank=True)
    nombre_original = models.CharField(max_length=255)
    tamano = models.BigIntegerField("tamaño", default=0)
    sha256 = models.CharField("huella SHA-256", max_length=64, db_index=True)

    editable = models.FileField("archivo editable", upload_to=ruta_archivo, max_length=300, blank=True)
    editable_nombre = models.CharField(max_length=255, blank=True)
    editable_tamano = models.BigIntegerField(default=0)
    editable_sha256 = models.CharField(max_length=64, blank=True)

    vista_previa = models.FileField(upload_to=ruta_derivado, max_length=300, blank=True,
                                    help_text="JPG generado (miniatura o conversión de HEIC).")
    fecha_toma = models.DateTimeField(null=True, blank=True)
    info = models.JSONField(default=dict, blank=True)

    subido_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    subido_en = models.DateTimeField(auto_now_add=True)
    aprobada_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name="+")
    aprobada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "versión de documento"
        verbose_name_plural = "versiones de documentos"
        ordering = ["-numero"]
        constraints = [models.UniqueConstraint(fields=["documento", "numero"], name="version_unica")]

    def __str__(self):
        return f"{self.documento} · Rev {self.revision}"

    @property
    def es_enlace(self):
        return bool(self.enlace)

    @property
    def drive(self):
        from .drive import analizar

        return analizar(self.enlace) if self.enlace else None

    # Formato que se muestra para un enlace de Drive (el enlace no lo dice): los de Google por su clase, y los
    # archivos de Drive según el tipo de documento.
    FORMATO_GOOGLE = {"document": "docx", "spreadsheets": "xlsx", "presentation": "pptx"}
    FORMATO_POR_TIPO = {"planos": "pdf", "reportes": "pdf", "permisos": "pdf", "normativas": "pdf", "contratos": "pdf",
                        "fotos": "jpg", "planillas": "xlsx", "presupuestos": "xlsx", "cronogramas": "xlsx"}

    @property
    def formato(self):
        """Extensión del archivo (o la que corresponde, si es un enlace de Drive): define el ícono."""
        if not self.enlace:
            return self.extension
        datos = self.drive or {}
        if datos.get("clase") == "carpeta":
            return "carpeta"
        return self.FORMATO_GOOGLE.get(datos.get("google")) or self.FORMATO_POR_TIPO.get(self.documento.tipo, "")

    @property
    def extension(self):
        if self.enlace:
            return ""
        return os.path.splitext(self.nombre_original)[1].lower().lstrip(".")

    @property
    def es_pdf(self):
        return self.extension == "pdf"

    @property
    def es_imagen(self):
        return self.extension in ("jpg", "jpeg", "png", "webp", "heic", "heif")

    @property
    def se_ve_en_navegador(self):
        return self.extension in ("pdf", "jpg", "jpeg", "png", "webp")

    @property
    def es_planilla(self):
        return self.extension in ("xlsx", "xlsm", "csv")
