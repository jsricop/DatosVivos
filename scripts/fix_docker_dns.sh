#!/usr/bin/env bash
#
# fix_docker_dns.sh — Reconfigura DNS para containers Docker.
#
# Problema: Docker daemon.json no soporta puerto custom en `dns`, asume :53.
# Solución: que dnscrypt-proxy escuche también en 172.17.0.1:53 (puerto
# estándar) y eliminamos el redirect iptables que no estaba funcionando.
#
# Uso: sudo bash fix_docker_dns.sh
#
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "❌ requiere root: sudo bash $0"
  exit 1
fi

TOML=/opt/dnscrypt-proxy/dnscrypt-proxy.toml

echo "==> 1. Limpiar regla iptables del intento anterior (si existe)"
iptables -t nat -D PREROUTING -i docker0 -p udp --dport 53 -j REDIRECT --to-ports 5053 2>/dev/null || true
iptables -t nat -D PREROUTING -i docker0 -p tcp --dport 53 -j REDIRECT --to-ports 5053 2>/dev/null || true
command -v netfilter-persistent >/dev/null && netfilter-persistent save >/dev/null 2>&1 || true

echo "==> 2. Configurar dnscrypt-proxy para escuchar en 172.17.0.1:53"
# La clave: agregar 172.17.0.1:53 a listen_addresses. Mantener 127.0.0.1:5053
# para que el host siga usándolo via systemd-resolved.
sed -i "s|^listen_addresses = \[.*\]|listen_addresses = ['127.0.0.1:5053', '172.17.0.1:53']|" "${TOML}"

echo "==> 3. Otorgar capability NET_BIND_SERVICE (binario real, no symlink)"
# Puertos <1024 requieren CAP_NET_BIND_SERVICE. Aplicar setcap al binario
# REAL (no al symlink en /usr/local/bin). El service unit ya tiene
# AmbientCapabilities=CAP_NET_BIND_SERVICE pero setcap es defensa extra.
DNSCRYPT_BIN=$(readlink -f /usr/local/bin/dnscrypt-proxy)
echo "   binario: ${DNSCRYPT_BIN}"
setcap 'cap_net_bind_service=+ep' "${DNSCRYPT_BIN}"

echo "==> 4. Reiniciar dnscrypt-proxy"
systemctl restart dnscrypt-proxy
sleep 3
systemctl is-active --quiet dnscrypt-proxy \
  && echo "   dnscrypt-proxy activo ✅" \
  || { echo "❌ no activo"; journalctl -u dnscrypt-proxy --no-pager -n 15; exit 1; }

echo ""
echo "==> 5. Verificación"
echo "--- Puertos en escucha ---"
ss -tlnp 2>/dev/null | grep -E "5053|172.17.0.1:53" | head
echo ""
echo "--- DNS desde host (puerto 53 del bridge) ---"
dig @172.17.0.1 -p 53 github.com +short +timeout=3 | head -2
echo ""
echo "--- DNS desde container alpine ---"
docker run --rm alpine:3.20 sh -c 'nslookup github.com 2>&1 | head -5'
echo ""
echo "--- HTTPS desde container ---"
docker run --rm alpine:3.20 sh -c 'wget -q -O- --timeout 8 https://www.datos.gov.co/api/views.json?limit=1 2>&1 | head -c 100; echo'

echo ""
echo "✅ DNS para containers funcionando. Ahora podés re-lanzar el build_index."
