#!/usr/bin/env bash
#
# setup_named_tunnel.sh — Migra de Cloudflare Quick Tunnel a Named Tunnel
# con dominio propio (datosvivos.co). URL fija que sobrevive reinicios.
#
# Pre-requisitos (manual, una sola vez):
#   1. Dominio registrado en Cloudflare (Registrar o nameservers apuntados).
#   2. Autenticar cloudflared contra tu cuenta:
#        cloudflared tunnel login
#      Esto imprime una URL — abrila en tu Mac, selecciona el dominio
#      "datosvivos.co" y autorizá. Se descarga el cert a ~/.cloudflared/cert.pem.
#
# Uso (en la VM, NO con sudo — cloudflared corre como usuario o vía systemd):
#   bash setup_named_tunnel.sh                              # default: datosvivos.co
#   TUNNEL_HOSTNAME=www.datosvivos.co bash setup_named_tunnel.sh   # subdomain alt
#
set -euo pipefail

# Configurables
TUNNEL_NAME="${TUNNEL_NAME:-datosvivos-prod}"
# Apex domain (datosvivos.co) en vez de subdomain (app.*) — Cloudflare
# maneja apex con CNAME-flattening automático.
TUNNEL_HOSTNAME="${TUNNEL_HOSTNAME:-datosvivos.co}"
LOCAL_SERVICE="${LOCAL_SERVICE:-http://localhost:8501}"
CONFIG_DIR="${HOME}/.cloudflared"

if [[ "${EUID}" -eq 0 ]]; then
  echo "❌ NO ejecutar con sudo. cloudflared crea archivos en ~/.cloudflared del usuario."
  echo "   Ejecutá como tu usuario normal: bash $0"
  exit 1
fi

# ─────────────────────────────────────────────────────────
echo "==> 1. Sanity check"
# ─────────────────────────────────────────────────────────

command -v cloudflared >/dev/null \
  || { echo "❌ cloudflared no instalado"; exit 1; }
echo "   cloudflared: $(cloudflared --version 2>&1 | head -1)"

if [[ ! -f "${CONFIG_DIR}/cert.pem" ]]; then
  echo ""
  echo "❌ No existe ~/.cloudflared/cert.pem"
  echo ""
  echo "Necesitás autenticar cloudflared primero:"
  echo "  cloudflared tunnel login"
  echo ""
  echo "Eso imprime una URL — abrila en tu navegador, seleccioná 'datosvivos.co'"
  echo "y autorizá. Después volvé a ejecutar este script."
  exit 1
fi
echo "   cert.pem: ✅ presente"

# Verificar Streamlit local
http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${LOCAL_SERVICE}/" || echo "000")
[[ "${http_code}" == "200" ]] \
  || { echo "❌ Streamlit no responde en ${LOCAL_SERVICE} (HTTP ${http_code})"; exit 1; }
echo "   Streamlit local: HTTP 200 ✅"

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 2. Crear/reutilizar Named Tunnel: ${TUNNEL_NAME}"
# ─────────────────────────────────────────────────────────

EXISTING_UUID=$(cloudflared tunnel list 2>/dev/null \
  | awk -v name="${TUNNEL_NAME}" '$2 == name {print $1}' | head -1)

if [[ -n "${EXISTING_UUID}" ]]; then
  echo "   tunnel '${TUNNEL_NAME}' ya existe → UUID ${EXISTING_UUID}"
  TUNNEL_UUID="${EXISTING_UUID}"
else
  echo "   creando nuevo tunnel..."
  cloudflared tunnel create "${TUNNEL_NAME}" 2>&1 | tee /tmp/tunnel_create.log
  TUNNEL_UUID=$(grep -oE '[a-f0-9-]{36}' /tmp/tunnel_create.log | head -1)
  [[ -n "${TUNNEL_UUID}" ]] \
    || { echo "❌ No pude extraer UUID del tunnel"; exit 1; }
  echo "   creado UUID ${TUNNEL_UUID}"
fi

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 3. Crear DNS record (${TUNNEL_HOSTNAME} → tunnel)"
# ─────────────────────────────────────────────────────────

# Si el record ya existe, cloudflared route dns lo actualiza (idempotente).
cloudflared tunnel route dns "${TUNNEL_NAME}" "${TUNNEL_HOSTNAME}" 2>&1 \
  | tee /tmp/tunnel_route.log

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 4. Generar config.yml"
# ─────────────────────────────────────────────────────────

CONFIG_FILE="${CONFIG_DIR}/config.yml"
cat > "${CONFIG_FILE}" <<EOF
# DatosVivos Named Tunnel config — generado por scripts/setup_named_tunnel.sh
tunnel: ${TUNNEL_UUID}
credentials-file: ${CONFIG_DIR}/${TUNNEL_UUID}.json

# Protocol http2 — TCP/7844 (autorizado por infra ANI).
# Sin esto, cloudflared prueba QUIC sobre UDP/7844 que sigue bloqueado.
protocol: http2

ingress:
  # Hostname principal → Streamlit local
  - hostname: ${TUNNEL_HOSTNAME}
    service: ${LOCAL_SERVICE}

  # Catch-all obligatorio: cualquier otro hostname/path responde 404.
  - service: http_status:404
EOF

echo "   ${CONFIG_FILE}:"
cat "${CONFIG_FILE}"

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 5. Reemplazar systemd service (Quick → Named)"
# ─────────────────────────────────────────────────────────

# El service file vive en /etc/systemd/system, requiere sudo.
SERVICE_FILE=/etc/systemd/system/datosvivos-tunnel.service

echo "   actualizando ${SERVICE_FILE} (requiere sudo)..."
sudo systemctl stop datosvivos-tunnel 2>/dev/null || true

sudo tee "${SERVICE_FILE}" > /dev/null <<EOF
[Unit]
Description=DatosVivos Cloudflare Named Tunnel (${TUNNEL_HOSTNAME})
Documentation=https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=${USER}
ExecStart=/usr/local/bin/cloudflared tunnel \\
  --config ${CONFIG_FILE} \\
  --no-autoupdate \\
  --loglevel info \\
  run ${TUNNEL_NAME}
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=${CONFIG_DIR}
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now datosvivos-tunnel
sleep 8

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 6. Verificación"
# ─────────────────────────────────────────────────────────

sudo systemctl is-active --quiet datosvivos-tunnel \
  && echo "   service: activo ✅" \
  || { echo "❌ service no activo"; sudo journalctl -u datosvivos-tunnel -n 25 --no-pager; exit 1; }

echo ""
echo "   esperando propagación DNS (~30 s)..."
sleep 30

PUBLIC_URL="https://${TUNNEL_HOSTNAME}/"
echo ""
echo "   Test HTTP desde la VM..."
ext_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "${PUBLIC_URL}" || echo "000")
echo "   ${PUBLIC_URL} → HTTP ${ext_code}"

if [[ "${ext_code}" =~ ^[23] ]]; then
  echo ""
  echo "🎉 Named Tunnel funcionando:"
  echo ""
  echo "    🌐 ${PUBLIC_URL}"
  echo ""
else
  echo ""
  echo "⚠️ HTTP ${ext_code} — DNS puede no haber propagado todavía."
  echo "   Reintentá en 1-2 min: curl -I ${PUBLIC_URL}"
  echo "   Logs: sudo journalctl -u datosvivos-tunnel -f"
fi

echo ""
echo "─────────────────────────────────────────────────────────"
echo "ℹ️  Mantenimiento:"
echo "   - Ver logs:     sudo journalctl -u datosvivos-tunnel -f"
echo "   - Reiniciar:    sudo systemctl restart datosvivos-tunnel"
echo "   - Detener:      sudo systemctl stop datosvivos-tunnel"
echo "   - URL fija:     ${PUBLIC_URL} (no cambia hasta que borres el DNS)"
echo "─────────────────────────────────────────────────────────"
