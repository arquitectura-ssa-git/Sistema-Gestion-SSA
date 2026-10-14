# Plan: Sistema de Gestión de Proyectos para estudio de arquitectura

## Estado de avance (al 14/10/2026)

| # | Sección | Estado |
|---|---|---|
| 1 | Base del sistema (proyecto, login, configuración, `setup.bat` / `run.bat`) | ✅ Hecho |
| 2 | Registro de actividad (auditoría inmutable) | ✅ Hecho: se guarda y está bloqueado contra cambios. Falta la pantalla para consultarlo. |
| 3 | Personal, áreas y clientes | ✅ Hecho |
| 4 | Obras y equipo | ✅ Hecho: lista con filtros, alta/edición, ficha con pestañas (resumen, equipo, hitos, actividad) |
| 4b | Proyectos, menú nuevo y plantillas de tareas | ✅ Hecho: menú Dashboard · Proyectos · Obras · Documentos · Equipo · Miembros · Clientes · Plantillas. Cada obra es de tipo *Proyecto* u *Obra* (se elige al crearla; códigos PR-/OB-). Plantillas de tareas con incidencia (suman 100%); al aplicarlas se copian a la pestaña *Tareas* y el avance sale de incidencia × avance de cada tarea. |
| 5 | Documentos (archivos, versiones, papelera) | ✅ Hecho: 10 tipos con datos propios, 3 niveles de acceso, versiones con huella, circuito de planos, vista previa de PDF/fotos/planillas, papelera. Diseño en `docs/SECCION-5-DOCUMENTOS.md` |
| 6 | Notificaciones (sistema, email, WhatsApp) | ⏭️ Sigue |
| 7 | Aprobaciones (gastos, decisiones y cambios) | ⏳ Pendiente |
| 8 | Comunicados (avisos al grupo y a clientes) | ⏳ Pendiente |
| 9 | Portal del cliente | ⏳ Pendiente. Hay una maqueta interactiva para mostrar: `demo/portal-cliente-demo.html` |
| 10 | Pruebas automáticas y datos demo | 🟡 Los datos demo están (`manage.py cargar_demo`). Faltan los tests automáticos. |

**Cambios respecto del plan original:**
- `Cliente` quedó en `apps/cuentas/` en vez de `apps/obras/`. Así se evita una dependencia circular entre las dos apps.
- Bootstrap y HTMX se cargan desde internet (CDN), no como archivos locales.

---

## Contexto
Un estudio de arquitectura necesita un sistema único donde:
- Cargar y ordenar la información de cada obra: planillas Excel, planos, normativas, presupuestos y cronogramas de obra.
- Asignar personal a cada área de la empresa (**Gerencia, Gestión de Obras, Gestión Administrativa, Gestión de Proyectos, Desarrollo de Proyectos, Dirección Técnica**) y a cada obra.
- Dar a los **clientes** un portal donde ven el avance de su obra y reciben notificaciones (en el sistema, por **email** y por **WhatsApp**) para **aprobar gastos y decisiones**.

Decisiones tomadas con el usuario: **Python**, **corre en local** por ahora, carpeta nueva en `D:\APLICACIONES`, **MVP por fases**.
Es un proyecto nuevo: `MIGUEL-RAG` es otro sistema (RAG de PDFs con Streamlit) y no se reutiliza en el MVP (quizás en la fase 3, para consultar normativas con IA).

## Stack recomendado
| Pieza | Elección | Por qué |
|---|---|---|
| Framework | **Django 5** | Trae login, usuarios, grupos/permisos, panel de administración en español, manejo de archivos y migraciones. Streamlit no sirve para un portal con roles. |
| Base de datos | **SQLite** en local → PostgreSQL al publicar | No hay que instalar nada; Django migra sin cambiar código. |
| Interfaz | Plantillas Django + **HTMX** + **Bootstrap 5** | Sin build de JavaScript; funciona en PC y celular. |
| Tareas en segundo plano | **Huey** con SQLite (worker en modo hilo, anda en Windows) | Envío de emails/WhatsApp y recordatorios sin frenar la página. |
| Excel | **openpyxl / pandas** | Leer planillas de presupuesto y cronograma. |
| Gantt / gráficos | **frappe-gantt**, **Chart.js** | Cronograma visual y avance. |
| Email | SMTP (ej. Gmail con clave de aplicación); en desarrollo se guardan en archivos | |
| WhatsApp | **Meta WhatsApp Cloud API** (o Twilio) detrás de una interfaz común | Requiere cuenta Business y plantillas aprobadas por Meta; en desarrollo, modo simulado. |

> ⚠️ **Importante sobre "local"**: si el sistema corre solo en una PC, los clientes no pueden entrar desde afuera y los links de los emails/WhatsApp no les van a abrir. Para probar con clientes reales hace falta publicarlo (fase 3) o un túnel temporal (Cloudflare Tunnel / ngrok).

## Estructura del proyecto
```
D:\APLICACIONES\GESTION-OBRAS\
  manage.py  requirements.txt  .env.example  setup.bat  run.bat  README.md
  config/            settings (español, zona horaria AR), urls, huey
  apps/
    core/            tablero, menú, comando cargar_demo
    cuentas/         Usuario propio, Cliente, Area, MiembroArea (rol: responsable | integrante), permisos
    auditoria/       RegistroActividad (solo agregar) + registrar()
    obras/           Obra, AsignacionObra (persona + área + función en la obra), Hito
    documentos/      Documento, VersionDocumento, visible_para_cliente, papelera
    aprobaciones/    Solicitud (gasto | decisión | cambio), OpcionDecision, historial
    notificaciones/  Notificacion, servicio `notificar()` + canales (interna, email, whatsapp)
    comunicados/     Comunicado, DestinatarioComunicado (lectura / acuse)
    portal/          vistas exclusivas del cliente
    finanzas/        (fase 2) Presupuesto, ItemPresupuesto, Gasto, Certificado
    cronograma/      (fase 2) Tarea, dependencias, % avance
    bitacora/        (fase 2) partes diarios, fotos de obra, incidencias
  templates/  static/
  media/             archivos subidos (fuera de git, NUNCA servidos públicamente)
```

## Modelo de permisos (el corazón del sistema)
- **Áreas** fijas (se cargan en una migración inicial): las 6 del estudio. Cada persona puede estar en una o más áreas, como *responsable* o *integrante*.
- **Gerencia** ve y administra todo: crea obras, asigna personal y ve finanzas.
- El resto ve **solo las obras donde está asignado** y actúa según su área:
  - Gestión de Obras → avance, bitácora, fotos, cronograma de ejecución.
  - Gestión Administrativa → presupuestos, gastos, facturas; **crea solicitudes de aprobación de gastos**.
  - Gestión de Proyectos → coordinación, cronograma, **solicitudes de decisión** al cliente.
  - Desarrollo de Proyectos → planos y documentación técnica con versiones.
  - Dirección Técnica → normativas, visto bueno técnico interno antes de enviar al cliente.
- **Cliente**: solo sus obras, solo documentos marcados "visible para cliente", sus solicitudes y notificaciones.
- Los archivos se descargan **a través de una vista que verifica permisos** (nunca un link directo a `media/`).
- Todo queda registrado: quién subió, quién aprobó, cuándo y desde dónde.

## Flujo de aprobaciones (gastos y decisiones)
1. Personal crea una **Solicitud**: tipo, título, descripción, monto (si es gasto), opciones A/B/C (si es decisión), adjuntos, fecha límite.
2. Opcional: la Dirección Técnica o la Gerencia la revisan antes de enviarla.
3. Al enviarla, `notificar()` crea la notificación interna y encola el **email** y el **WhatsApp** con un link firmado y con vencimiento a la solicitud.
4. El cliente entra al portal → **Aprueba / Rechaza / Pide cambios** (o elige una opción) con comentario.
5. Se notifica al creador y a los responsables del área; hay recordatorios automáticos si vence el plazo.
6. Estados: borrador → en revisión interna → enviada → aprobada | rechazada | con observaciones | vencida.

## Panel de administración (para el personal que carga información)
Un panel propio, no el admin técnico de Django, pensado para el personal del estudio:
- **Administrador de archivos**: ver todo lo que cargó (o su área) por obra y categoría; subir, reemplazar con nueva versión, renombrar, mover de carpeta, marcar/desmarcar "visible para cliente" y archivar. En vez de borrar se usa una **papelera** con restauración, y solo Gerencia puede borrar definitivamente.
- **Enviar comunicados**: redactar un mensaje (con adjuntos opcionales) y elegir destinatarios: **un área**, **el equipo de una obra**, **el cliente de una obra**, **todos los clientes** o personas puntuales. También se eligen los canales (sistema, email, WhatsApp). Usa el mismo servicio `notificar()`.
- **Confirmación de lectura**: cada destinatario queda con estado *enviado → entregado → leído*, y opcionalmente con **"acuse de recibo"** (botón "Recibido/Conforme").
- **Registro asentado (auditoría)**: una tabla `RegistroActividad` de solo agregar (nunca se edita ni se borra) que guarda quién hizo qué, sobre qué objeto, cuándo, desde qué IP y el detalle del cambio. Cubre subidas, versiones, cambios de visibilidad, comunicados, aprobaciones y cambios de personal. Se ve por obra (línea de tiempo) y de forma global para Gerencia, con filtros y **exportación a Excel/PDF**.
- Permisos: cada persona administra los archivos de sus obras/área; los responsables de área administran los de su área; Gerencia administra todo.

## Fases
### Fase 0 — Base (setup)
- Proyecto Django, `setup.bat` / `run.bat` (mismo estilo que MIGUEL-RAG), `.env` para claves.
- Usuario propio (login por email), admin en español, plantilla base con menú según rol.
- Comando `python manage.py cargar_demo`: áreas, un usuario por área, un cliente y una obra de ejemplo con documentos.

### Fase 1 — MVP
1. **Áreas y personal**: pantalla de Gerencia para dar de alta personas y designarlas en áreas.
2. **Obras**: alta de obra (cliente, dirección, fechas, etapa), asignación de personal por área, ficha de obra con pestañas.
3. **Documentos**: carga múltiple con arrastrar y soltar, categorías (Planos, Planillas, Normativas, Presupuestos, Cronogramas, Contratos, Fotos, Otros), **versiones** (Rev A, B, C…), vista previa de PDF e imágenes, descarga de DWG/XLSX, búsqueda por nombre y etiquetas.
4. **Aprobaciones** con el flujo descrito arriba.
5. **Notificaciones**: campana interna + email.
6. **Panel de administración**: administrador de archivos con papelera, envío de comunicados a grupos y clientes con confirmación de lectura, y registro de actividad asentado.
7. **Portal cliente**: resumen de la obra (etapa, % avance, próximos hitos), documentos compartidos, solicitudes pendientes, historial de decisiones.

### Fase 2 — Gestión operativa
- **WhatsApp** (Cloud API) enchufado en el mismo servicio de notificaciones.
- **Presupuestos**: importar Excel → rubros/ítems; presupuesto vs gastado; los gastos aprobados impactan solos.
- **Cronograma**: importar Excel → tareas; Gantt; % avance que alimenta el portal.
- **Bitácora de obra**: parte diario, fotos desde el celular, incidencias.
- **Tablero de Gerencia**: obras activas, desvíos de costo/plazo, aprobaciones trabadas.

### Fase 3 — Publicación y extras
- Publicar (VPS o Railway + PostgreSQL + almacenamiento de archivos), HTTPS y backups.
- Portal instalable en el celular (PWA) con notificaciones push.
- Reportes PDF semanales para el cliente; consulta de normativas con IA (reutilizando la idea de MIGUEL-RAG).

## Archivos clave del MVP
- `config/settings.py` — idioma, zona horaria, apps, archivos, email, Huey.
- `apps/cuentas/models.py` — `Usuario`, `Cliente`, `Area`, `MiembroArea`.
- `apps/cuentas/permisos.py` — reglas de acceso: `obras_visibles()`, `puede_editar_obra()`, `documentos_visibles()` y decoradores de vistas.
- `apps/auditoria/services.py` — `registrar()`.
- `apps/obras/models.py` — `Obra`, `AsignacionObra`, `Hito`.
- `apps/documentos/models.py` + `views.py` — versiones y descarga protegida.
- `apps/aprobaciones/models.py` + `services.py` — máquina de estados de `Solicitud`.
- `apps/notificaciones/services.py` + `canales/{interna,email,whatsapp}.py` — `notificar(usuario, evento, objeto)`.
- `apps/portal/views.py` — vistas del cliente.

## Verificación
- **Tests (pytest-django)** sobre permisos: un cliente no ve la obra de otro cliente; no descarga documentos no visibles; un integrante no ve obras donde no está asignado; Gerencia ve todo.
- **Tests del flujo**: crear solicitud → envío → notificación creada y email en la bandeja de archivos → el cliente aprueba → el creador recibe la notificación; el link firmado vencido es rechazado.
- **Tests del panel**: un comunicado a "equipo de obra" llega solo a los asignados; la lectura y el acuse quedan registrados; cada acción genera un `RegistroActividad` y ese registro no se puede modificar ni borrar desde la interfaz ni desde el admin.
- **Prueba manual**: `setup.bat` → `cargar_demo` → `run.bat` → entrar como Administración, crear un gasto y enviarlo → entrar como cliente en otra ventana (incógnito), aprobar → verificar el estado y las notificaciones. Verificar en vista de celular con el navegador integrado.
