#!/usr/bin/env bash
# Instala (o reinstala) el sistema de gestión en un VPS con Ubuntu 24.04 / 22.04 o Debian 12.
#
# Uso, como root en el VPS:
#   curl -fsSL https://raw.githubusercontent.com/arquitectura-ssa-git/Sistema-Gestion-SSA/main/deploy/instalar.sh \
#     | bash -s -- sophia.saezsanchez.com.ar tu-email@ejemplo.com
#
# Se puede volver a correr sin perder datos: actualiza el código y la configuración,
# pero nunca toca la base de datos ni los archivos subidos.
#
# Para cambiar la dirección, se vuelve a correr con la nueva y la vieja en DOMINIO_ANTERIOR
# (la vieja queda redirigiendo a la nueva):
#   curl ... | DOMINIO_ANTERIOR=marta.saezsanchez.com.ar bash -s -- sophia.saezsanchez.com.ar tu-email@ejemplo.com
set -euo pipefail

DOMINIO="${1:-}"
EMAIL="${2:-}"
REPO="${REPO:-https://github.com/arquitectura-ssa-git/Sistema-Gestion-SSA.git}"
RAMA="${RAMA:-main}"
USUARIO="gestion"
BASE="/srv/gestion"
APP="$BASE/app"
RESPALDOS="$BASE/respaldos"
DOMINIO_ANTERIOR="${DOMINIO_ANTERIOR:-}"

paso() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m[!] %s\033[0m\n' "$*"; }
error() { printf '\033[1;31m[x] %s\033[0m\n' "$*" >&2; exit 1; }

[ "$(id -u)" -eq 0 ] || error "Corré este script como root (en la terminal de Hostinger ya sos root)."
[ -n "$DOMINIO" ] && [ -n "$EMAIL" ] || error "Faltan datos. Uso: bash instalar.sh gestion.tudominio.com tu-email@ejemplo.com"
. /etc/os-release
case "${ID:-}" in
  ubuntu|debian) ;;
  *) error "Este VPS tiene ${PRETTY_NAME:-un sistema desconocido}. Cambialo a Ubuntu 24.04 desde hPanel (VPS → Sistema operativo)." ;;
esac

paso "Instalando programas del sistema (puede tardar unos minutos)"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-dev build-essential git nginx certbot python3-certbot-nginx \
  sqlite3 ufw cron curl sudo >/dev/null

paso "Preparando el usuario y las carpetas"
# Algunos proveedores dejan el nombre del VPS sin resolver y sudo avisa "unable to resolve host".
grep -qw "$(hostname)" /etc/hosts || echo "127.0.1.1 $(hostname)" >> /etc/hosts
id "$USUARIO" >/dev/null 2>&1 || useradd --system --create-home --home-dir "$BASE" --shell /usr/sbin/nologin "$USUARIO"
mkdir -p "$BASE" "$RESPALDOS"
chown "$USUARIO:$USUARIO" "$BASE"
chmod 750 "$BASE"
chown root:root "$RESPALDOS"
chmod 700 "$RESPALDOS"
como() { sudo -u "$USUARIO" -H "$@"; }

paso "Bajando el código ($RAMA)"
if [ -d "$APP/.git" ]; then
  como git -C "$APP" fetch -q origin "$RAMA"
  como git -C "$APP" checkout -q "$RAMA"
  como git -C "$APP" reset -q --hard "origin/$RAMA"
else
  como git clone -q --branch "$RAMA" "$REPO" "$APP"
fi

paso "Instalando el sistema en su entorno de Python"
[ -x "$APP/.venv/bin/python" ] || como python3 -m venv "$APP/.venv"
como "$APP/.venv/bin/pip" install -q --upgrade pip
como "$APP/.venv/bin/pip" install -q -r "$APP/deploy/requirements-servidor.txt"

paso "Configuración (.env)"
if [ ! -f "$APP/.env" ]; then
  CLAVE="$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')"
  cat > "$APP/.env" <<EOF
NOMBRE_ESTUDIO=Saez Sanchez Arquitectos
SECRET_KEY=$CLAVE
DEBUG=false
ALLOWED_HOSTS=$DOMINIO
CSRF_TRUSTED_ORIGINS=https://$DOMINIO
SITIO_URL=https://$DOMINIO
CONFIAR_EN_PROXY=true
ZONA_HORARIA=America/Argentina/Buenos_Aires
DEFAULT_FROM_EMAIL=Saez Sanchez Arquitectos <no-responder@$DOMINIO>
WHATSAPP_BACKEND=simulado
TAREAS_INMEDIATAS=true
ENLACE_DIAS_VALIDEZ=7
MAX_ARCHIVO_MB=300
EOF
  chown "$USUARIO:$USUARIO" "$APP/.env"
  chmod 600 "$APP/.env"
else
  # Se conserva todo (clave secreta, etc.); solo se pone al día la dirección del sistema.
  sed -i -e "s|^ALLOWED_HOSTS=.*|ALLOWED_HOSTS=$DOMINIO|" \
         -e "s|^CSRF_TRUSTED_ORIGINS=.*|CSRF_TRUSTED_ORIGINS=https://$DOMINIO|" \
         -e "s|^SITIO_URL=.*|SITIO_URL=https://$DOMINIO|" \
         -e "s|no-responder@[^>]*>|no-responder@$DOMINIO>|" "$APP/.env"
  echo "Ya existe; se actualizó la dirección a $DOMINIO."
fi

paso "Base de datos y archivos estáticos"
como "$APP/.venv/bin/python" "$APP/manage.py" migrate --noinput
como "$APP/.venv/bin/python" "$APP/manage.py" collectstatic --noinput -v0

paso "Servicio del sistema (arranca solo al prender el VPS)"
cat > /etc/systemd/system/gestion.service <<EOF
[Unit]
Description=Sistema de gestión de proyectos y obras
After=network.target

[Service]
User=$USUARIO
Group=$USUARIO
WorkingDirectory=$APP
RuntimeDirectory=gestion
ExecStart=$APP/.venv/bin/gunicorn config.wsgi:application --bind unix:/run/gestion/gunicorn.sock --workers 3 --timeout 300 --umask 007
Restart=always

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q gestion
systemctl restart gestion

paso "Servidor web (nginx)"
usermod -aG "$USUARIO" www-data
IPV6=""
IPV6_DEFAULT=""
if [ -s /proc/net/if_inet6 ]; then
  IPV6="listen [::]:80;"
  IPV6_DEFAULT="listen [::]:80 default_server;"
fi
cat > /etc/nginx/sites-available/gestion <<EOF
# Cualquier pedido que no venga por la dirección del sistema (bots que prueban la IP) se corta.
server {
    listen 80 default_server;
    $IPV6_DEFAULT
    server_name _;
    return 444;
}

server {
    listen 80;
    $IPV6
    server_name $DOMINIO;

    client_max_body_size 310M;

    location /static/ {
        alias $APP/staticfiles/;
        expires 7d;
    }

    location / {
        proxy_pass http://unix:/run/gestion/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$remote_addr;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300;
    }
}
EOF
if [ -n "$DOMINIO_ANTERIOR" ]; then
  cat >> /etc/nginx/sites-available/gestion <<EOF

# Dirección anterior: lleva a la nueva.
server {
    listen 80;
    $IPV6
    server_name $DOMINIO_ANTERIOR;
    return 301 https://$DOMINIO\$request_uri;
}
EOF
fi
ln -sf /etc/nginx/sites-available/gestion /etc/nginx/sites-enabled/gestion
rm -f /etc/nginx/sites-enabled/default
nginx -t -q
systemctl restart nginx

paso "Firewall (solo SSH y web)"
# Muchos proveedores usan otro puerto para SSH (ej. 22022): se abren el 22 y los que use el servidor,
# para no quedar afuera del VPS al activar el firewall.
PUERTOS_SSH="22 $(sshd -T 2>/dev/null | awk '/^port /{print $2}' | tr '\n' ' ')"
[ -n "${SSH_CONNECTION:-}" ] && PUERTOS_SSH="$PUERTOS_SSH $(echo "$SSH_CONNECTION" | awk '{print $4}')"
for PUERTO in $(echo "$PUERTOS_SSH" | tr ' ' '\n' | sort -un); do
  ufw allow "$PUERTO/tcp" >/dev/null
done
echo "Puertos SSH abiertos: $(echo "$PUERTOS_SSH" | tr ' ' '\n' | sort -un | tr '\n' ' ')"
ufw allow 'Nginx Full' >/dev/null
ufw --force enable >/dev/null

paso "Certificado de seguridad (HTTPS)"
IP_VPS="$(curl -fsS -4 https://ifconfig.me 2>/dev/null || true)"
IP_DNS="$(getent ahostsv4 "$DOMINIO" 2>/dev/null | awk 'NR==1{print $1}' || true)"
if [ -n "$IP_DNS" ] && [ "$IP_DNS" = "$IP_VPS" ]; then
  certbot --nginx -d "$DOMINIO" --non-interactive --agree-tos -m "$EMAIL" --redirect -q \
    || aviso "No se pudo sacar el certificado. Volvé a correr este script en un rato."
  if [ -n "$DOMINIO_ANTERIOR" ]; then
    certbot --nginx -d "$DOMINIO_ANTERIOR" --non-interactive --agree-tos -m "$EMAIL" --redirect -q \
      || aviso "No se pudo sacar el certificado de $DOMINIO_ANTERIOR (la dirección vieja); la nueva anda igual."
  fi
else
  aviso "$DOMINIO todavía no apunta a este VPS (apunta a '${IP_DNS:-nada}', el VPS es '${IP_VPS:-?}')."
  aviso "Creá el registro DNS (ver guía), esperá unos minutos y volvé a correr este mismo comando."
fi

paso "Copias de seguridad diarias (3 AM, se guardan 14 días)"
cat > /usr/local/bin/sophia-respaldo <<EOF
#!/usr/bin/env bash
set -euo pipefail
umask 077
FECHA=\$(date +%Y-%m-%d_%H%M)
TMP=\$(mktemp -d)
sqlite3 "$APP/data/db.sqlite3" ".backup '\$TMP/db.sqlite3'"
cp "$APP/.env" "\$TMP/env"
tar -czf "$RESPALDOS/respaldo_\$FECHA.tar.gz" -C "\$TMP" db.sqlite3 env -C "$APP" media 2>/dev/null \\
  || tar -czf "$RESPALDOS/respaldo_\$FECHA.tar.gz" -C "\$TMP" db.sqlite3 env
rm -rf "\$TMP"
find "$RESPALDOS" -name 'respaldo_*.tar.gz' -mtime +14 -delete
echo "Respaldo guardado: $RESPALDOS/respaldo_\$FECHA.tar.gz"
EOF
chmod 700 /usr/local/bin/sophia-respaldo
echo "0 3 * * * root /usr/local/bin/sophia-respaldo >/dev/null 2>&1" > /etc/cron.d/sophia-respaldo

# Atajo para correr comandos del sistema: sophia-manage createsuperuser, sophia-manage cargar_demo, etc.
# (sudo descarta las variables de entorno: createsuperuser pide la contraseña en pantalla).
cat > /usr/local/bin/sophia-manage <<EOF
#!/usr/bin/env bash
cd "$APP" && sudo -u "$USUARIO" -H "$APP/.venv/bin/python" manage.py "\$@"
EOF
chmod 755 /usr/local/bin/sophia-manage

# Atajo para actualizar con lo último de GitHub.
cat > /usr/local/bin/sophia-actualizar <<EOF
#!/usr/bin/env bash
set -euo pipefail
/usr/local/bin/sophia-respaldo
sudo -u "$USUARIO" -H git -C "$APP" fetch -q origin "$RAMA"
sudo -u "$USUARIO" -H git -C "$APP" reset -q --hard "origin/$RAMA"
sudo -u "$USUARIO" -H "$APP/.venv/bin/pip" install -q -r "$APP/deploy/requirements-servidor.txt"
sophia-manage migrate --noinput
sophia-manage collectstatic --noinput -v0
systemctl restart gestion
echo "Sistema actualizado."
EOF
chmod 700 /usr/local/bin/sophia-actualizar

# Los comandos de antes (marta-*) siguen andando.
for C in respaldo manage actualizar; do ln -sf "/usr/local/bin/sophia-$C" "/usr/local/bin/marta-$C"; done
rm -f /etc/cron.d/marta-respaldo

sleep 2
if systemctl is-active -q gestion && curl -fsS -o /dev/null -H "Host: $DOMINIO" http://127.0.0.1/cuenta/login/; then
  paso "¡Listo! El sistema está funcionando."
else
  aviso "El sistema no respondió. Mandá la salida de: journalctl -u gestion -n 50 --no-pager"
fi
cat <<EOF

  Dirección:        https://$DOMINIO
  Crear tu usuario: sophia-manage createsuperuser
  Actualizar:       sophia-actualizar
  Respaldo ahora:   sophia-respaldo   (quedan en $RESPALDOS)

EOF
