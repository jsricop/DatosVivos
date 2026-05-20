#!/usr/bin/env bash
#
# setup_doh_vm.sh — Configura DNS-over-HTTPS en la VM de ANI con dnscrypt-proxy.
#
# Por qué: la VM tiene salida TCP/443 abierta a internet (post-ticket
# infraestructura ANI 2026-05-19) pero los DNS internos `192.168.200.150`
# y `192.168.200.250` no resuelven dominios públicos, y UDP/53 saliente
# a `1.1.1.1`/`8.8.8.8` está bloqueado. Como TCP/443 sí funciona, se
# instala `dnscrypt-proxy` como resolver local que hace DoH (DNS-over-HTTPS)
# a Cloudflare/Quad9/etc por HTTPS.
#
# NOTA HISTÓRICA: en 2026-05-20 detectamos que `cloudflared proxy-dns`
# (que era nuestra primera opción) fue deprecado por Cloudflare en la
# versión 2026.2.0+. dnscrypt-proxy es la alternativa robusta y mantenida.
#
# Es idempotente: se puede ejecutar varias veces sin efectos colaterales.
#
# Uso (en la VM, con sudo):
#   sudo bash setup_doh_vm.sh
#
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "❌ Este script requiere root. Ejecutá: sudo bash $0"
  exit 1
fi

DNSCRYPT_VERSION="2.1.15"
DNSCRYPT_URL="https://github.com/DNSCrypt/dnscrypt-proxy/releases/download/${DNSCRYPT_VERSION}/dnscrypt-proxy-linux_x86_64-${DNSCRYPT_VERSION}.tar.gz"
INSTALL_DIR="/opt/dnscrypt-proxy"
BIN_DIR="/usr/local/bin"
LISTEN_PORT="5053"

echo "==> 0. Limpieza de instalación previa (idempotencia)"
systemctl stop cloudflared-dns 2>/dev/null || true
systemctl disable cloudflared-dns 2>/dev/null || true
rm -f /etc/systemd/system/cloudflared-dns.service
systemctl stop dnscrypt-proxy 2>/dev/null || true
systemctl daemon-reload

echo "==> 1. Descargando dnscrypt-proxy ${DNSCRYPT_VERSION} (vía DoH)"
TMP_TAR="$(mktemp -t dnscrypt.XXXXXX.tar.gz)"
curl -fsSL --doh-url https://1.1.1.1/dns-query \
  -o "${TMP_TAR}" \
  "${DNSCRYPT_URL}"
mkdir -p "${INSTALL_DIR}"
tar -xzf "${TMP_TAR}" -C "${INSTALL_DIR}" --strip-components=1
rm -f "${TMP_TAR}"
chmod +x "${INSTALL_DIR}/dnscrypt-proxy"
ln -sf "${INSTALL_DIR}/dnscrypt-proxy" "${BIN_DIR}/dnscrypt-proxy"
echo "    versión instalada: $(${BIN_DIR}/dnscrypt-proxy -version)"

echo "==> 2. Configurando dnscrypt-proxy con DNS Stamps estáticos"
# IMPORTANTE: usamos stamps hardcoded (IPs estáticas + SNI) en lugar de
# [sources.public-resolvers] porque cualquier fuente remota necesitaría DNS
# para resolverse, y DNS es justamente lo que estamos arreglando (huevo-gallina).
# Stamps verificados de https://dnscrypt.info/stamps/ (Cloudflare, Google, Quad9).
cat > "${INSTALL_DIR}/dnscrypt-proxy.toml" <<EOF
# DatosVivos — DoH local resolver con servidores hardcoded por stamp.
listen_addresses = ['127.0.0.1:${LISTEN_PORT}']
server_names = ['cloudflare', 'google', 'quad9-doh']
ipv4_servers = true
ipv6_servers = false
dnscrypt_servers = false
doh_servers = true
require_dnssec = false
require_nolog = true
require_nofilter = false
force_tcp = false
timeout = 5000
keepalive = 30
cache = true
cache_size = 4096
cache_min_ttl = 600
cache_max_ttl = 86400
cache_neg_min_ttl = 60
cache_neg_max_ttl = 600

# CRÍTICO: desactivar features que requieren DNS de bootstrap o conexión previa.
ignore_system_dns = true
netprobe_timeout = -1   # desactiva el "estoy conectado a internet" precheck
bootstrap_resolvers = []  # no usamos resolvers de bootstrap

[static]

  [static.'cloudflare']
  stamp = 'sdns://AgcAAAAAAAAABzEuMC4wLjEAEmRucy5jbG91ZGZsYXJlLmNvbQovZG5zLXF1ZXJ5'

  [static.'google']
  stamp = 'sdns://AgUAAAAAAAAABzguOC44LjggsKKKE4EwvtIbNjGjagI2607EdKSVHowYZtyvD9iPrkkHOC44LjguOAovZG5zLXF1ZXJ5'

  [static.'quad9-doh']
  stamp = 'sdns://AgMAAAAAAAAABzkuOS45LjkgsBkgdEu7dsmrBT4B4Ht-BQ5HPSD3n3vqQ1-v5DydJC8SZG5zOS5xdWFkOS5uZXQ6NDQzCi9kbnMtcXVlcnk'
EOF

# El usuario para correr el daemon (sin privilegios extra)
if ! id -u dnscrypt &>/dev/null; then
  useradd --system --no-create-home --shell /usr/sbin/nologin dnscrypt
fi
chown -R dnscrypt:dnscrypt "${INSTALL_DIR}"

echo "==> 3. Creando servicio systemd dnscrypt-proxy"
cat > /etc/systemd/system/dnscrypt-proxy.service <<EOF
[Unit]
Description=DNSCrypt-proxy DoH resolver (DatosVivos)
Documentation=https://github.com/DNSCrypt/dnscrypt-proxy/wiki
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dnscrypt
Group=dnscrypt
WorkingDirectory=${INSTALL_DIR}
ExecStart=${BIN_DIR}/dnscrypt-proxy -config ${INSTALL_DIR}/dnscrypt-proxy.toml
Restart=always
RestartSec=3
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=${INSTALL_DIR}
ProtectHome=yes
PrivateTmp=yes
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now dnscrypt-proxy
sleep 4

if systemctl is-active --quiet dnscrypt-proxy; then
  echo "    dnscrypt-proxy: activo ✅"
else
  echo "❌ Servicio no activo. Últimas líneas del log:"
  journalctl -u dnscrypt-proxy --no-pager -n 25
  exit 1
fi

echo "==> 4. Configurando systemd-resolved para usar el DoH local"
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/datosvivos-doh.conf <<EOF
# DatosVivos — DNS-over-HTTPS via dnscrypt-proxy local (127.0.0.1:${LISTEN_PORT}).
# Reemplaza los DNS internos (192.168.200.x) para resolver dominios públicos
# sin abrir UDP/53 saliente. Reversible con:
#   sudo systemctl disable --now dnscrypt-proxy
#   sudo rm /etc/systemd/resolved.conf.d/datosvivos-doh.conf
#   sudo systemctl restart systemd-resolved
[Resolve]
DNS=127.0.0.1:${LISTEN_PORT}
FallbackDNS=
Domains=~.
DNSStubListener=yes
EOF

# Asegurar que /etc/resolv.conf apunta al stub de systemd-resolved
if [ ! -L /etc/resolv.conf ] || [ "$(readlink /etc/resolv.conf)" != "../run/systemd/resolve/stub-resolv.conf" ]; then
  ln -sf ../run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
fi

systemctl restart systemd-resolved
sleep 2

echo ""
echo "==> 5. Verificación"
echo "--- resolvectl status (DNS activos) ---"
resolvectl status | grep -E "(Current DNS|DNS Servers|DNS Domain)" | head -6
echo ""
echo "--- Resolución DNS pública ---"
for d in github.com www.datos.gov.co ollama.com pypi.org huggingface.co api.cloudflare.com; do
  ip=$(getent hosts "$d" 2>/dev/null | awk '{print $1}' | head -1)
  printf "  %-25s → %s\n" "$d" "${ip:-NO RESUELVE ❌}"
done
echo ""
echo "--- HTTPS sin --doh-url (ahora con DNS estándar) ---"
for url in https://github.com https://www.datos.gov.co https://ollama.com https://api.cloudflare.com/client/v4/; do
  printf "  %-45s " "$url"
  curl -s -o /dev/null -w "HTTP %{http_code} en %{time_total}s\n" --max-time 8 "$url"
done

echo ""
echo "✅ DoH configurado. La VM resuelve DNS público vía dnscrypt-proxy (DoH a Cloudflare/Google/Quad9)."
echo "   Servicio: systemctl status dnscrypt-proxy"
echo "   Logs:     sudo journalctl -u dnscrypt-proxy -f"
echo "   Revertir: sudo systemctl disable --now dnscrypt-proxy && sudo rm /etc/systemd/resolved.conf.d/datosvivos-doh.conf && sudo systemctl restart systemd-resolved"
