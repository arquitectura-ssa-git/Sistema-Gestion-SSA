# Plan: Sistema de Gestión de Proyectos para estudio de arquitectura

## Estado de avance (al 13/11/2026)

| # | Sección | Estado |
|---|---|---|
| 1 | Base del sistema (proyecto, login, configuración, `setup.bat` / `run.bat`) | ✅ Hecho |
| 2 | Registro de actividad (auditoría inmutable) | ✅ Hecho: se guarda y está bloqueado contra cambios. Falta la pantalla para consultarlo. |
| 3 | Personal, áreas y clientes | ✅ Hecho |
| 4 | Obras y equipo | ✅ Hecho: lista con filtros, alta/edición, ficha con pestañas (resumen, equipo, hitos, actividad) |
| 4b | Proyectos, menú nuevo y plantillas de tareas | ✅ Hecho: menú Dashboard · Proyectos · Obras · Documentos · Equipo · Miembros · Clientes · Plantillas. Cada obra es de tipo *Proyecto* u *Obra* (se elige al crearla; códigos PR-/OB-). Plantillas de tareas con incidencia (suman 100%); al aplicarlas se copian a la pestaña *Tareas* y el avance sale de incidencia × avance de cada tarea. |
| 5 | Documentos (archivos, versiones, papelera) | ✅ Hecho: 10 tipos con datos propios, 3 niveles de acceso, versiones con huella, circuito de planos, vista previa de PDF/fotos/planillas, papelera. Diseño en `docs/SECCION-5-DOCUMENTOS.md` |
| 6 | Notificaciones (sistema, email, WhatsApp) | ⏸️ En pausa: avisos de hitos por WhatsApp analizados (ver «Temas en pausa»). El email del servidor tampoco está configurado. |
| 7 | Aprobaciones (gastos, decisiones y cambios) | ⏳ Pendiente |
| 8 | Comunicados (avisos al grupo y a clientes) | ⏳ Pendiente |
| 9 | Portal del cliente | ⏳ Pendiente. Hay una maqueta interactiva para mostrar: `demo/portal-cliente-demo.html` |
| 10 | Pruebas automáticas y datos demo | ✅ Datos demo (`manage.py cargar_demo`) y pruebas automáticas en `tests/` (pytest). |
| 11 | Gestión de Adquisiciones (pedidos de materiales, contrataciones y presupuestos) | 📝 En diseño (ver abajo). Reemplaza el tablero de Trello |
| 12 | Informes diarios de Dirección Técnica | ✅ Hecho (09/11/2026). Falta el informe semanal para el cliente |
| 13 | Time Report (carga de horas, feriados, pedidos de habilitación, reportes, tipos de tarea editables) | ✅ Hecho. DIR ve el del equipo; jornada automática con ausencias para la Asistente de Dirección |
| 14 | Dashboard de DIR | ✅ Hecho (11/11/2026). Opcional: presupuesto de horas por proyecto |
| 15 | Asistente de Dirección, Legajos del personal y Agenda (sincronizada con Clientes) | ✅ Hecho (12/11/2026) |
| 16 | Ayuda (videos y preguntas frecuentes) | ✅ Hecho: 3 videos (Time Report, crear proyecto, avance y tareas) |
| 17 | Importar proyectos y clientes desde Excel | ✅ Hecho |
| 18 | Publicación en el VPS (sophia.saezsanchez.com.ar, HTTPS, respaldo diario) | ✅ Hecho |
| 19 | Preguntale a SOPHIA (asistente que responde consultas sobre los datos; después por WhatsApp) | 📝 En diseño (ver abajo) |

## Módulos en diseño

### 11 · Gestión de Adquisiciones — se hace dentro de SOPHIA (decidido por Pablo el 13/11/2026)
Usa lo que ya existe: proyectos y obras, equipos y responsables, permisos de montos, documentos y registro de actividad.

**Qué se pide:** materiales, contrataciones profesionales y presupuestos de contratistas, siempre de una obra o un
proyecto. Datos: listado de ítems con cantidades, fecha del pedido y fecha de entrega. **Lleva montos.**

**Circuito de obra** (lo carga el DT; lo gestiona la Asistente de Compras):
Recepción de pedido → Solicitud de cotización → Orden de compra → Autorización DIR → Facturación → Compra →
Logística y entrega → Recepción en obra.

**Circuito de proyecto** (lo carga el Responsable de proyecto, con el presupuesto ya pedido):
Pedido con presupuesto → Autorización DIR → Orden de compra.

**Proveedores:** ficha y seguimiento de cuenta (órdenes, facturas, pagos, saldo).

**Pantallas previstas:** tablero por estados (como Trello) y lista con filtros; ficha del pedido con ítems, montos,
adjuntos e historial; autorización de DIR con botón y comentario.

**Etapas:** 1) pedidos y circuito de estados; 2) cotizaciones, órdenes de compra con montos y autorización DIR;
3) proveedores y cuenta.

**Definido con Pablo (13/11/2026):**
- Los DT cargan los pedidos desde la obra; **Gestión de Compras (Julieta)** hace el seguimiento y el resto del proceso.
- El DT **ve los montos de sus pedidos**.
- Si DIR no autoriza, **elige**: «Devolver para corregir» (vuelve a Compras con comentario y se reenvía) o
  «Rechazar definitivo» (se cierra y el DT recibe el motivo). El comentario es obligatorio en los dos casos.
- Maqueta aprobada antes de programar: tablero, carga desde el celular, ficha y autorización de DIR.

**Falta definir:** una o varias cotizaciones por pedido (la maqueta muestra hasta 3); recepción parcial; quién
registra los pagos; si se migran los pedidos abiertos de Trello.

### 12 · Informes diarios de Dirección Técnica
**Quién y cuándo:** el DT de la obra, desde SOPHIA (normalmente en el celular, en la obra). Uno por obra y por día,
se carga hasta las 23:59 de ese día. Después queda cerrado; corregirlo requiere **autorización de DIR** (mismo
mecanismo que la habilitación del Time Report) y la corrección queda registrada.

**Qué lleva:**
- Fecha y clima (sol / lluvia); si se pudo trabajar en obra (y por qué no, si no).
- Personal por gremio: Albañilería, Electricistas, Plomeros, Pintores, Herreros, etc. (cantidad de personas).
- Avance de tareas: se toma del avance de la plantilla de la obra (las barras que mueva ese día quedan en el informe
  y en el historial de avance).
- Fotos de las tareas en ejecución, con detalle (se achican solas al subirlas para no llenar el servidor).
- Notas de pedido dejadas en el libro de obra.
- Observaciones.

**Quién lo lee:** DIR y Coordinación de Obras.

**Registro:** listado de informes por obra (pestaña nueva en la obra) para la trazabilidad del avance: días
trabajados y perdidos por lluvia, personal por gremio en el tiempo, avance día a día.

**Más adelante:** informe semanal filtrado para el cliente (se diseña junto con el portal y los avisos).

**Definido con Pablo:** lo carga solo el DT; clima sol o lluvia (con lluvia se pregunta si se pudo trabajar); la
lista de gremios la editan los DT y Coordinación de Obras; la nota de pedido es texto más foto de la hoja del libro.
Hasta 20 fotos por informe; el aviso de «sin informe» sale solo los días hábiles.

### 19 · Preguntale a SOPHIA — pedido por Pablo el 13/11/2026
**Qué es:** un asistente al que DIR le pregunta con sus palabras y responde con los datos del sistema.
Ej.: «¿cuántas horas lleva el proyecto Pérez?», «¿qué obras no mandaron informe esta semana?», «¿a quién se le vence
el contrato?». Por ahora solo consultas; nada de informes programados.

**Cómo funciona:** SOPHIA llama a Claude (API de Anthropic, modelo `claude-opus-5-5`, esfuerzo bajo) con un juego de
**herramientas de solo lectura** escritas en Django. Claude elige cuáles usar, SOPHIA las ejecuta **con los permisos
del usuario que pregunta** y Claude redacta la respuesta. No hay acceso libre a la base ni SQL: solo esas consultas.

**Herramientas previstas:** buscar obras/proyectos (estado, etapa, avance, plazo, responsables); detalle de una obra
(tareas, hitos, historial de avance, certificados si puede ver montos); horas (por persona, proyecto, tipo y fechas);
informes diarios (por obra y fechas: clima, días perdidos, gremios); legajos (qué falta y qué vence — nunca el
contenido de los archivos); agenda (buscar un contacto); resumen del tablero de DIR.

**Etapas:**
1. Cuadro «Preguntale a SOPHIA» en el Dashboard de DIR (web y celular). Sirve para probar y ajustar las respuestas.
2. Por WhatsApp con Kapso: Pablo escribe al número de SOPHIA y recibe la respuesta. Como la conversación la empieza
   él, no hace falta plantilla aprobada por Meta. Solo responde a números autorizados (el de DIR).
3. Opcional: habilitarlo a Coordinación con sus permisos.

**Reglas:** solo lee; respeta permisos (montos solo a quien los ve); cada pregunta queda en el registro de actividad;
la clave de Anthropic va solo en el `.env` del VPS; los datos consultados viajan a Anthropic para armar la respuesta
(los archivos de legajos no se mandan).

**Costo estimado:** unos US$ 0,05 a 0,10 por pregunta → con 10 preguntas por día hábil, unos US$ 10 a 20 por mes.
Kapso: plan gratis (2.000 mensajes/mes).

**Falta de Pablo:** crear la cuenta en console.anthropic.com con medio de pago y generar la clave (la carga él en el
servidor; nunca por chat); para la etapa 2, la cuenta de Kapso y el número de WhatsApp.

## Temas en pausa (para retomar)

### Avisos de WhatsApp a clientes cuando se cumple un hito — analizado el 09/11/2026
**Qué se quiere:** al marcar como cumplido un hito *visible para el cliente*, mandar un WhatsApp a los contactos de
ese cliente que tengan activado «recibir avisos por WhatsApp». En SOPHIA ya existen `Hito` (`completado`,
`visible_cliente`) y en los contactos los campos `telefono` y `notif_whatsapp`.

**Regla de Meta:** como el cliente no escribió antes, hace falta una **plantilla aprobada** (categoría «utilidad»),
p. ej. «Hola {{nombre}}, en la obra {{obra}} se cumplió el hito {{hito}} el {{fecha}}». Meta cobra cada envío.

**Opciones evaluadas:**
| | Vocero CRM (github.com/kevinrivm/vocero-crm) | Kapso (docs.kapso.ai) |
|---|---|---|
| SOPHIA puede mandar el aviso | No: su API solo responde conversaciones abiertas; las plantillas se mandan a mano desde su pantalla. Habría que modificarlo | Sí: API con clave para crear y enviar plantillas |
| Instalar en el VPS | Sí (Docker + PostgreSQL, ~2 GB RAM) | No (servicio en la nube) |
| Seguir usando el WhatsApp del celular | No (el número pasa a la API) | Sí («coexistencia» con WhatsApp Business) |
| Costo de la herramienta | Gratis (código abierto) | Plan gratis: 2.000 mensajes/mes, 1 número |
| Datos | En el servidor propio | En Kapso |

Tercera opción: hablar directo con la Cloud API de Meta (sin intermediario, pero con alta en Meta más engorrosa y
sin coexistencia).

**Recomendación:** Kapso. Vocero sirve como bandeja de WhatsApp con agente de IA, no para avisos desde otro sistema.

**Pasos al retomar:** 1) aprobar el cambio en la SPEC (hoy los avisos por WhatsApp figuran como pendientes);
2) probar con el número de prueba de Kapso; 3) crear la plantilla «hito cumplido» y esperar la aprobación de Meta;
4) en SOPHIA, enviar el aviso al cumplirse un hito visible y registrarlo en la actividad (la clave de Kapso va solo
en el `.env` del VPS); 5) probar con un número propio y recién después conectar el número del estudio.

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
