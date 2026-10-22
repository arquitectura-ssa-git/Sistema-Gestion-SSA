# SPEC · SOPHIA

**Sistema de Obras y Proyectos · Inteligencia Arquitectónica** — Saez Sanchez Arquitectos, Tucumán.

Esta es la ley máxima del sistema: dice qué es, para quién y qué reglas no se rompen. Ningún pedido la contradice
sin que lo decida quien aprueba (sección 7). Antes de cada cambio, Claude Code la lee y, si el pedido choca con
algo de acá, se detiene y pregunta.

---

## 1. Propósito

Reunir en un solo lugar los proyectos, las obras, los archivos, el equipo y las horas del estudio, para saber en
todo momento cuánto avanzó cada trabajo, quién está en él y cuántas horas lleva, sin depender de planillas sueltas,
carpetas compartidas ni mensajes.

## 2. Usuarios y roles

El personal del estudio se organiza en **seis áreas**. Cada persona pertenece a una o más, como **responsable** o
como **integrante**.

| Área | Rol en el sistema |
|---|---|
| Gerencia (**DIR**) | Ve y administra todo |
| Gestión de Proyectos | Su responsable es **Coordinación de Proyectos** |
| Gestión de Obras | Su responsable es **Coordinación de Obras** |
| Desarrollo de Proyectos | Producción de proyectos |
| Dirección Técnica | Aprueba planos para obra |
| Gestión Administrativa | Clientes y administración |

**Coordinación** = responsables de Gestión de Proyectos o de Gestión de Obras.

Qué puede hacer cada uno:

| Qué | Quién |
|---|---|
| Ver todos los **proyectos** | Todo el personal |
| Ver una **obra** | Su equipo asignado; Coordinación, el responsable de Gestión Administrativa y DIR ven todas |
| Ver los archivos de un proyecto u obra | Su equipo asignado; Coordinación, el responsable de Gestión Administrativa y DIR ven todos |
| Editar datos, tareas y avance de un proyecto u obra | Sus responsables y DIR |
| Crear proyectos y obras | DIR |
| Ver **montos** (presupuesto, certificados, saldos) | Solo DIR y el responsable de Gestión Administrativa |
| Ver el **historial de avance** | DIR, Coordinación y el responsable de Gestión Administrativa |
| Importar un certificado de avance (Excel) | Responsables de la obra, DIR y el responsable de Gestión Administrativa |
| Subir archivos | A un proyecto u obra: su equipo asignado, Coordinación y DIR. A la Biblioteca general: todo el personal |
| Aprobar planos para obra | Dirección Técnica |
| Crear y editar plantillas de tareas | Gestión de Proyectos, Gestión de Obras y DIR |
| Cargar sus propias horas (Time Report) | Todo el personal, en cualquier proyecto u obra activo |
| Habilitar carga tardía de horas y ver reportes | Coordinación de Proyectos y DIR |
| Cargar clientes | Gestión Administrativa y DIR |
| Dar de alta usuarios y definir sus días y horas | DIR |
| Editar el calendario de feriados | DIR |
| Borrar un documento definitivamente (desde la papelera) | DIR |

En los listados, cada persona ve **primero** los proyectos y obras donde está en el equipo (en negrita y con un
punto) y después el resto.

**Clientes:** existen como fichas con sus contactos. El portal para que el cliente entre al sistema todavía no está
activo (ver sección 5).

## 3. Reglas que nunca se rompen

**Seguridad y datos**
1. **Nunca** se guardan contraseñas, claves ni datos personales sensibles en el código ni en GitHub. Las claves del
   servidor viven solo en el `.env` del VPS. Las contraseñas de los usuarios se guardan cifradas y nadie las puede leer.
2. Los datos reales (base de datos y archivos subidos) viven **solo en el VPS**. Las copias locales usan datos de
   prueba (`manage.py cargar_demo`).
3. El **registro de actividad** no se modifica ni se borra, ni desde la pantalla ni desde el panel técnico.
4. Los archivos se ven y se descargan **solo** a través del sistema, que controla los permisos en cada pedido. Nunca
   por una dirección directa.
5. Nada se borra de entrada: los documentos van a la **papelera**. Solo DIR puede borrarlos definitivamente, y el
   registro de actividad conserva que existieron.
6. Antes de cada actualización del servidor se hace una copia de seguridad (`sophia-actualizar` la hace sola), y hay
   una copia automática todas las noches.
7. Nunca se borra el historial de GitHub ni se fuerza una subida.

**Time Report**
8. Las horas se cargan de a **media hora** (0,5).
9. Cada persona carga el día de **hoy hasta las 23:59**. Un día pasado solo se carga con una **habilitación**
   aprobada por Coordinación de Proyectos o DIR, y vale hasta las 23:59 del día en que se aprueba. Los días futuros
   no se cargan nunca.
10. Las horas **normales** no superan las horas contratadas de esa persona para ese día de la semana (cada persona
    tiene las suyas, de lunes a viernes). Lo que pasa de eso es **extra**.
11. Sábados, domingos y feriados: todo lo que se carga es extra.
12. En un feriado que cae de lunes a viernes, la jornada de cada persona se computa sola como paga.

**Tareas y avance**
13. Las tareas se organizan en **Etapas → Rubros → Ítems**. Las incidencias de cada grupo suman siempre **100%**:
    al cambiar una, las demás se reajustan.
14. El avance de rubros, etapas y del proyecto se **calcula solo** a partir del avance de los ítems. No se carga a mano.
15. Cada cambio de avance de un ítem queda en el **historial** con su fecha y quién lo hizo (por la barra, el editor o
    un certificado). Editar el listado **no** borra el historial: cada fila se actualiza en su lugar.
16. Un certificado importado **manda**: el listado de la obra queda igual al del Excel, con la incidencia de cada rubro
    e ítem según su monto. Las filas con el mismo código y nombre conservan su historial. Un mismo número de
    certificado no se carga dos veces.
17. Los montos nunca se muestran a quien no tiene permiso: no viajan al editor de tareas ni a otras pantallas.
18. Aplicar una plantilla a un proyecto **copia** las tareas: cambiar el proyecto no cambia la plantilla.

**Forma**
19. Todo el sistema está en **español**, con voseo («cargá», «elegí»).
20. La estética sigue el manual de marca de Saez Sanchez: **monocromática** (negro, gris plomo, grises y blanco
    roto), tipografía Creato Display, sin colores de acento.
21. Todo tiene que funcionar también en el **celular**.

## 4. Decisiones fijas

No se cambian sin acuerdo (sección 7):

- **Django 5.2** (Python), con **SQLite** como base de datos.
- **Bootstrap 5** y **HTMX**, cargados desde CDN. Íconos de Bootstrap Icons.
- Tipografía **Creato Display**, guardada en el propio sistema.
- Servidor: **VPS con Ubuntu 22.04**, nginx + gunicorn, certificado HTTPS de Let's Encrypt, copias diarias a las 3 AM
  que se guardan 14 días.
- Dirección: **https://sophia.saezsanchez.com.ar** (la vieja, marta.saezsanchez.com.ar, redirige). DNS en Wix.
- Código en GitHub: **arquitectura-ssa-git/Sistema-Gestion-SSA**. Se trabaja en una rama por cambio y se une a
  `main` con un pull request.
- Publicar: merge en GitHub y después `sophia-actualizar` en el VPS.

## 5. Funciones terminadas y congeladas

Andan y **no se tocan salvo pedido explícito**. Si un arreglo necesita tocar una de estas, Claude avisa antes y
explica por qué.

| Función | Qué hace |
|---|---|
| Ingreso | Email y contraseña; pantalla con el logo de SOPHIA |
| Menú | Dashboard · Proyectos · Obras · Documentos · Equipo · Clientes · Plantillas · Time Report |
| Dashboard | Proyectos y obras activos de cada uno, horas de hoy, pedidos, permisos por vencer, planos para revisar |
| Proyectos y Obras | Listas separadas; creación desde plantilla o copiando otro proyecto; duplicar; ficha con pestañas |
| Tareas | Árbol Etapa → Rubro → Ítem con incidencias, código, unidad y cantidad; barras de avance que se guardan solas; «Ver solo rubros» |
| Historial de avance | Fecha de cada cambio de avance; cuándo empezó y terminó cada ítem y cuántos días tardó |
| Certificados | Importar el Excel del contratista (uno por quincena); montos por certificado y presupuesto por rubro |
| Plantillas | Plantilla base «Proyecto de Arquitectura»; guardar un proyecto como plantilla |
| Documentos | Tipos con datos propios, versiones, estados de planos, tres niveles de acceso, papelera |
| Equipo | Personal agrupado (DIR, Coordinación, áreas); alta de usuarios con días y horas por día |
| Clientes | Fichas de clientes y sus contactos |
| Time Report | Carga diaria, extras, «Repetir», habilitaciones, reportes con exportación a Excel, feriados |
| Registro de actividad | Guarda cada acción; no se puede modificar |

**Pendientes** (todavía no existen; no se dan por hechas): notificaciones, aprobaciones de gastos y decisiones,
comunicados, portal del cliente, pantalla para consultar el registro de actividad, envío de emails desde el
servidor (hoy «Olvidé mi contraseña» y las invitaciones no llegan).

## 6. Cómo se trabaja

- **Un botón por vez:** una pantalla o una acción. Se hace, se prueba, se guarda y recién después se pasa al siguiente.
- Antes de programar, cada botón tiene su ficha: qué hace, quién lo usa, dónde aparece, qué datos toca, **qué no
  debe tocar**, cómo se prueba y cuándo está terminado.
- Cada botón queda con su **prueba automática**, y antes de guardar pasan todas las pruebas, no solo la nueva.
- Un error se arregla como un botón más: primero la causa, después una prueba que lo reproduce y el arreglo mínimo.
- Se prueba a mano en el navegador, también en tamaño celular, con los usuarios de prueba.
- Cada cambio se guarda con un commit que dice qué hizo, en español.
- Lo hecho y lo que sigue se anota en **PLAN.md**.
- Una conversación con Claude Code por botón: al terminar, se empieza una nueva.

## 7. Cómo se cambia esta SPEC

Solo con el **OK de Pablo Saez (DIR)**. Claude Code nunca la modifica por su cuenta: propone el cambio y espera la
aprobación. Cada cambio se anota abajo con fecha y motivo.

| Fecha | Cambio | Motivo | Aprobó |
|---|---|---|---|
| 22/10/2026 | Primera versión | Ordenar las reglas del sistema según el manual de buenas prácticas | Pendiente |
| 22/10/2026 | Montos solo para DIR y Gestión Administrativa; historial de avance; certificados de obra | Pedido para la obra MZ (certificados quincenales) | Pablo Saez (lo pidió) |
| 22/10/2026 | El historial de avance lo ven solo DIR, Coordinación y el responsable de Gestión Administrativa | Pedido de Pablo | Pablo Saez (lo pidió) |
