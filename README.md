# MARTA · Gestión de proyectos y obras

Sistema para un estudio de arquitectura: obras, equipo por área, archivos (planos, planillas, fotos,
permisos…), aprobaciones del cliente y registro de todo lo que pasa. Corre en esta PC.

El plan completo y el estado de cada sección están en [PLAN.md](PLAN.md).

## Instalar (una sola vez)

1. Instalá **Python 3.10 o más nuevo** (tildá "Add Python to PATH").
2. Doble clic en **`setup.bat`**: crea el entorno, instala todo y prepara la base de datos.
3. Opcional: copiá `.env.example` como `.env` y completá el nombre del estudio, el email, etc.

## Usar

- Doble clic en **`run.bat`**. Se abre http://127.0.0.1:8000.
- Para crear el primer usuario de Gerencia:
  ```
  .venv\Scripts\python.exe manage.py createsuperuser
  ```

## Datos de prueba

```
.venv\Scripts\python.exe manage.py cargar_demo
```

Carga una persona por área, dos clientes, un proyecto (Edificio Sur), una obra (Casa Pérez), dos plantillas de
tareas y documentos de ejemplo. Todos los usuarios de prueba
usan la contraseña **`Demo2026!`** (solo para probar en esta PC).

| Email | Quién es |
|---|---|
| gerencia@demo.local | Lucía Gómez · Gerencia (ve todo; también entra a la administración técnica) |
| obras@demo.local | Juan Ruiz · Gestión de Obras (responsable de Casa Pérez) |
| administracion@demo.local | Laura Sosa · Gestión Administrativa |
| proyectos@demo.local | Diego Paz · Gestión de Proyectos (en las dos obras) |
| desarrollo@demo.local | Sofía Luna · Desarrollo de Proyectos |
| tecnica@demo.local | Pablo Vera · Dirección Técnica (aprueba planos) |
| cliente@demo.local | Carlos Pérez · cliente de Casa Pérez |
| cliente2@demo.local | Ana Torres · cliente de Edificio Sur |

## Plantillas y avance por tareas

En **Plantillas** se arman listados modelo de tareas, cada una con su **incidencia** (cuánto pesa en el total;
entre todas suman 100%). En un proyecto u obra, pestaña **Tareas**, se elige una plantilla: las tareas se copian
y se pueden ajustar sin tocar la plantilla. A medida que se ejecutan se carga el avance de cada tarea y el avance
total se calcula solo (suma de incidencia × avance). Pueden crear y editar plantillas Gerencia, Gestión de
Proyectos y Gestión de Obras; las tareas de cada obra las editan sus responsables.

## Publicarlo en internet

Para tenerlo en un VPS con dirección propia y HTTPS, seguí [docs/INSTALAR-EN-VPS.md](docs/INSTALAR-EN-VPS.md).

## Time Report (horas)

Cada persona carga sus horas del día en **Time Report**: proyecto u obra (o "Estudio / sin proyecto"), tipo de
tarea (Producción, Gestión, Administración, Compras, Capacitación), horas de a 0,5 y si son extra. Las horas
normales no pueden pasar la jornada de la persona ese día (en Miembros se tildan los días que viene y cuántas horas; sábados y domingos todo es extra).
Solo se puede cargar el día de hoy hasta las 23:59; para un día pasado se pide habilitación y la aprueban
Gerencia o el coordinador de proyectos (responsable de Gestión de Proyectos). Ellos ven además los reportes por
proyecto, persona o tipo de tarea, exportables a Excel, y la pestaña **Horas** de cada proyecto.

## Dónde queda cada cosa

| Qué | Dónde |
|---|---|
| Base de datos | `data/db.sqlite3` |
| Archivos subidos | `media/` (por obra y tipo, con nombres internos; se bajan solo desde el sistema) |
| Emails (en desarrollo no se envían) | `data/emails/` |
| Diseño de la sección de documentos | `docs/SECCION-5-DOCUMENTOS.md` |

> **Copias de seguridad:** antes de usarlo con datos reales hay que copiar `data/` y `media/` todos los días
> a otro disco o a la nube.

> El **registro de actividad no se puede borrar**, ni siquiera desde la base de datos. Por eso `manage.py flush`
> falla, y no se puede borrar un usuario ni una obra con actividad: se desactivan.
