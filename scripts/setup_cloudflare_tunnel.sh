#!/usr/bin/env bash
#
# setup_cloudflare_tunnel.sh — Levanta Cloudflare Tunnel (Quick) hacia Streamlit local.
#
# Qué hace:
#   - Crea un servicio systemd `datosvivos-tunnel` que corre `cloudflared
#     tunnel --url http://localhost:8501` en background con Restart=always.
#   - El tunnel inicia conexión SALIENTE a Cloudflare por **TCP/7844**
#     (puerto oficial — requiere autorización en firewalls corporativos
#     que solo abran 443). Forzamos --protocol http2 para evitar QUIC
#     sobre UDP/7844 que muchos firewalls bloquean por default.
#   - Cloudflare genera una URL pública aleatoria `https://xxx.trycloudflare.com`
#     con cert TLS válido y enruta a la Streamlit interna.
#
# Limitaciones del modo Quick:
#   - URL cambia con cada reinicio del tunnel. No es "fija".
#   - No requiere cuenta ni dominio Cloudflare. Útil para piloto y demo jurado.
#   - Para URL fija, comprar dominio + Named Tunnel (próximo script).
#
# Uso (en la VM):
#   sudo bash setup_cloudflare_tunnel.sh
#
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "❌ requiere root: sudo bash $0"
  exit 1
fi

LOCAL_URL="http://localhost:8501"
SERVICE_FILE=/etc/systemd/system/datosvivos-tunnel.service

# ─────────────────────────────────────────────────────────
echo "==> 1. Verificación previa"
# ─────────────────────────────────────────────────────────

command -v cloudflared >/dev/null \
  || { echo "❌ cloudflared no instalado (esperado de setup_doh_vm.sh)"; exit 1; }
echo "   cloudflared: $(cloudflared --version 2>&1 | head -1)"

http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "${LOCAL_URL}/" || echo "000")
if [[ "${http_code}" != "200" ]]; then
  echo "❌ Streamlit no responde en ${LOCAL_URL} (HTTP ${http_code})."
  echo "   Asegurate de que el container está up: sudo docker compose ps"
  exit 1
fi
echo "   Streamlit local: HTTP 200 ✅"

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 2. Servicio systemd datosvivos-tunnel"
# ─────────────────────────────────────────────────────────

# Detener instancia previa (idempotencia)
systemctl stop datosvivos-tunnel 2>/dev/null || true

cat > "${SERVICE_FILE}" <<EOF
[Unit]
Description=DatosVivos Cloudflare Quick Tunnel
Documentation=https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=nobody
ExecStart=/usr/local/bin/cloudflared tunnel \\
  --url ${LOCAL_URL} \\
  --protocol http2 \\
  --no-autoupdate \\
  --loglevel info
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
# Protección: solo networking outbound, sin filesystem writes.
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now datosvivos-tunnel
echo "   service activado, esperando que Cloudflare asigne URL..."
sleep 10

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 3. Extraer URL pública del log"
# ─────────────────────────────────────────────────────────

PUBLIC_URL=""
for attempt in 1 2 3 4 5; do
  PUBLIC_URL=$(journalctl -u datosvivos-tunnel -n 200 --no-pager 2>/dev/null \
    | grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' \
    | head -1 || true)
  [[ -n "${PUBLIC_URL}" ]] && break
  echo "   intento ${attempt}/5: aún no aparece la URL, esperando 5 s..."
  sleep 5
done

if [[ -z "${PUBLIC_URL}" ]]; then
  echo ""
  echo "⚠️ No encontré la URL en el log tras 35 s. Diagnóstico:"
  systemctl status datosvivos-tunnel --no-pager | head -15
  echo ""
  echo "Últimas líneas del log:"
  journalctl -u datosvivos-tunnel -n 25 --no-pager
  exit 1
fi

# ─────────────────────────────────────────────────────────
echo ""
echo "==> 4. URL pública asignada"
# ─────────────────────────────────────────────────────────
echo ""
echo "    🌐 ${PUBLIC_URL}"
echo ""

echo "==> 5. Smoke test desde fuera (vía Cloudflare)"
ext_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 12 "${PUBLIC_URL}/" || echo "000")
if [[ "${ext_code}" == "200" ]]; then
  echo "   HTTP 200 ✅ — la URL responde públicamente con TLS válido"
else
  echo "   HTTP ${ext_code} ⚠️ — el tunnel arrancó pero la URL aún no responde 200."
  echo "   Espera 30 s y reintenta: curl -I ${PUBLIC_URL}/"
fi

echo ""
echo "─────────────────────────────────────────────────────────"
echo "ℹ️  Mantenimiento:"
echo "   - Ver logs:     sudo journalctl -u datosvivos-tunnel -f"
echo "   - Reiniciar:    sudo systemctl restart datosvivos-tunnel"
echo "   - Detener:      sudo systemctl stop datosvivos-tunnel"
echo "   - URL nueva:    al reiniciar el servicio Cloudflare asigna otro subdominio."
echo "─────────────────────────────────────────────────────────"
