#!/usr/bin/env bash
# Despliegue de JARVIS en un servidor Ubuntu (Oracle Cloud, Hetzner, PC viejo...).
#
# Uso, dentro de la carpeta del repo ya copiada en el servidor:
#     sudo bash deploy/deploy.sh
#
# Deja JARVIS como servicio (arranca solo, se reinicia si falla) y le pone una
# contraseña aleatoria. Al terminar te muestra la URL y la contraseña.
set -euo pipefail

PORT="${JARVIS_PORT:-8765}"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SERVICE_USER="${SUDO_USER:-$(whoami)}"

echo "==> 1/6 Instalando dependencias del sistema"
apt-get update -y
apt-get install -y python3-venv python3-pip git curl openssl

echo "==> 2/6 Creando el entorno virtual"
sudo -u "$SERVICE_USER" python3 -m venv "$APP_DIR/.venv"
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install --upgrade pip -q
sudo -u "$SERVICE_USER" "$APP_DIR/.venv/bin/pip" install -r "$APP_DIR/requirements.txt" -q

echo "==> 3/6 Configurando .env"
PASS=""
if [ ! -f "$APP_DIR/.env" ]; then
  cp "$APP_DIR/.env.example" "$APP_DIR/.env"
  PASS="$(openssl rand -base64 18 | tr -dc 'A-Za-z0-9' | cut -c1-16)"
  # Quita claves previas y añade las del servidor.
  sed -i '/^JARVIS_HOST=/d;/^JARVIS_PORT=/d;/^JARVIS_PASSWORD=/d' "$APP_DIR/.env"
  {
    echo "JARVIS_HOST=0.0.0.0"
    echo "JARVIS_PORT=$PORT"
    echo "JARVIS_PASSWORD=$PASS"
  } >> "$APP_DIR/.env"
  chown "$SERVICE_USER" "$APP_DIR/.env"
else
  echo "    (.env ya existe; no lo toco)"
  PASS="$(grep -E '^JARVIS_PASSWORD=' "$APP_DIR/.env" | cut -d= -f2- || true)"
fi

echo "==> 4/6 Abriendo el puerto $PORT en el cortafuegos local"
if command -v iptables >/dev/null 2>&1; then
  # Oracle Ubuntu bloquea todo salvo SSH: hay que abrir el puerto también aquí.
  iptables -C INPUT -p tcp --dport "$PORT" -j ACCEPT 2>/dev/null || \
    iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$PORT" -j ACCEPT || true
  netfilter-persistent save 2>/dev/null || true
fi

echo "==> 5/6 Creando el servicio (arranque automático)"
cat > /etc/systemd/system/jarvis.service <<EOF
[Unit]
Description=JARVIS Personal
After=network-online.target
Wants=network-online.target

[Service]
User=$SERVICE_USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$APP_DIR/.venv/bin/python -m jarvis.server
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable jarvis >/dev/null 2>&1
systemctl restart jarvis

echo "==> 6/6 Comprobando"
sleep 3
systemctl --no-pager --lines=0 status jarvis || true

IP="$(curl -s --max-time 5 ifconfig.me || echo 'IP-DEL-SERVIDOR')"
cat <<EOF

============================================================
 JARVIS está en marcha.

   URL:        http://$IP:$PORT
   Contraseña: ${PASS:-(la que pusiste en .env)}

 Si no abre, revisa la regla de entrada (ingress) en la
 consola de Oracle: abre el puerto TCP $PORT.

 Comandos útiles:
   sudo systemctl status jarvis     (estado)
   sudo systemctl restart jarvis    (reiniciar)
   sudo journalctl -u jarvis -f     (ver registros en vivo)
============================================================
EOF
