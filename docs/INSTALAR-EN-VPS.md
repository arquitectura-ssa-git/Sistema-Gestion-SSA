# Publicar MARTA en el VPS

Resultado: el sistema queda en **https://marta.saezsanchez.com.ar**, prendido las 24 horas, con candado de
seguridad (HTTPS) y una copia de seguridad automática todas las noches.

Se hace una sola vez y lleva unos 20 minutos.

## 1. Que el VPS tenga Ubuntu

En el panel del proveedor, entrá al VPS (**Administrar**) y fijate qué **sistema operativo** tiene.

- Si dice **Ubuntu 24.04** (o 22.04) o **Debian 12**: seguí al paso 2.
- Si dice otra cosa: buscá la opción **Reinstalar / Cambiar sistema operativo** y elegí **Ubuntu 24.04**.
  Esto borra el VPS, así que hacelo solo si no tiene nada que importe.

## 2. Apuntar la dirección al VPS (DNS)

Entrá donde está administrado el dominio `saezsanchez.com.ar` (el proveedor donde lo compraron o donde está
la web del estudio) y buscá **Zona DNS** o **Registros DNS**. Agregá uno nuevo:

| Tipo | Nombre | Valor | TTL |
|---|---|---|---|
| A | `marta` | `143.95.174.234` (la IP del VPS) | 3600 (o el que venga) |

No toques los otros registros: la web y el correo del estudio siguen igual.
El cambio puede tardar de 5 minutos a un par de horas en verse.

## 3. Abrir la terminal del VPS

En el panel del VPS hay un botón de **consola** o **terminal** (un ícono de pantalla con `>_`). Abrilo e ingresá
como `root` con la contraseña del VPS.

## 4. Instalar

Pegá este comando (todo en una línea; cambiá el email por uno de ustedes, es para los avisos del certificado):

```
curl -fsSL https://raw.githubusercontent.com/arquitectura-ssa-git/Sistema-Gestion-SSA/main/deploy/instalar.sh | bash -s -- marta.saezsanchez.com.ar arquitectura@saezsanchez.com.ar
```

Tarda unos 5 minutos. Al final tiene que decir **¡Listo! El sistema está funcionando.**

Si avisa que **la dirección todavía no apunta a este VPS**, es que el DNS del paso 2 todavía no se propagó.
Esperá un rato y volvé a pegar el mismo comando: es seguro repetirlo, no borra nada.

## 5. Crear tu usuario

En la misma terminal:

```
marta-manage createsuperuser
```

Te pide email y contraseña (al escribir la contraseña no se ve nada; es normal). Ese es el usuario de Gerencia.

Listo: entrá a **https://marta.saezsanchez.com.ar**.

## Comandos útiles (en la terminal del VPS)

| Para | Comando |
|---|---|
| Traer la última versión de GitHub | `marta-actualizar` (hace una copia de seguridad antes) |
| Hacer una copia de seguridad ahora | `marta-respaldo` |
| Ver las copias guardadas | `ls /srv/gestion/respaldos` |
| Ver si el sistema está andando | `systemctl status gestion` |
| Ver errores | `journalctl -u gestion -n 50 --no-pager` |

## Dónde queda cada cosa en el VPS

| Qué | Dónde |
|---|---|
| Sistema | `/srv/gestion/app` |
| Base de datos | `/srv/gestion/app/data/db.sqlite3` |
| Archivos subidos | `/srv/gestion/app/media/` |
| Configuración (clave secreta, dominio) | `/srv/gestion/app/.env` |
| Copias de seguridad (14 días) | `/srv/gestion/respaldos/` |

> Las copias quedan en el mismo VPS. Cada tanto bajá una a tu PC o a Google Drive: si el VPS se pierde, se
> pierden con él.
