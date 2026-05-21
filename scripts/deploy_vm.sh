#!/usr/bin/env bash
#
# deploy_vm.sh — Deploy producción de DatosVivos en la VM ANI (Beta-1).
#
# Stack final (modo "como producción"):
#   • Ollama en host (recomendación oficial, evita overhead Docker).
#   • mcp-server + streamlit en Docker Compose.
#   • dnscrypt-proxy escuchando en 127.0.0.1 (host) Y bridge Docker (172.17.0.1)
#     para que los containers puedan resolver DNS por DoH.
#   • Cloudflare Tunnel se monta después con scripts/setup_cloudflare_tunnel.sh.
#
# Idempotente — re-ejecutable sin daño.
#
# Uso (en la VM, como usuario regular NO root, NO con sudo):
#   bash deploy_vm.sh
#
set -euo pipefail

REPO_URL="https://github.com/jsricop/DatosVivos.git"
REPO_DIR="${HOME}/DatosVivos"
OLLAMA_MODEL="qwen2.5-coder:3b"
DOCKER_BRIDGE_IP="172.17.0.1"
DOH_PORT="5053"
LOG_DIR="${HOME}/datosvivos-logs"

# UID/GID del usuario host — los pasamos como build-args a los Dockerfiles
# para que `appuser` dentro del container tenga los mismos IDs.
# Esto evita problemas de permisos en bind mounts de ./data al container.
export APP_UID="$(id -u)"
export APP_GID="$(id -g)"

if [[ "${EUID}" -eq 0 ]]; then
  echo "❌ No ejecutar como root. Usá: bash $0"
  exit 1
fi

mkdir -p "${LOG_DIR}"

# ────────────────────────────────────────────────────────────────────
echo "==> 1. Sanity check"
# ────────────────────────────────────────────────────────────────────
command -v git >/dev/null || { echo "❌ git no encontrado"; exit 1; }
echo "   git:        $(git --version)"

getent hosts github.com >/dev/null \
  || { echo "❌ DNS no resuelve github.com. ¿Está activo dnscrypt-proxy?"; exit 1; }
echo "   dns (host): OK"

http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 8 https://www.datos.gov.co || echo "000")
[[ "${http_code}" =~ ^[23] ]] || { echo "❌ datos.gov.co devuelve ${http_code}"; exit 1; }
echo "   https:      OK (${http_code})"

avail_gb=$(df --output=avail -BG ~ | tail -1 | tr -d 'G ')
[[ "${avail_gb}" -ge 10 ]] || { echo "❌ Disco insuficiente: ${avail_gb}G (necesitamos ≥10G)"; exit 1; }
echo "   disco:      ${avail_gb}G libres ✅"

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 2. Docker Engine + Compose plugin"
# ────────────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null; then
  echo "   instalando Docker oficial (apt repo)..."
  # Limpiar instalaciones viejas si las hubo
  sudo apt-get -qq remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true
  sudo apt-get -qq update
  sudo apt-get -qq install -y ca-certificates curl gnupg
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
    | sudo gpg --dearmor --batch --yes -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  codename=$(. /etc/os-release; echo "${UBUNTU_CODENAME:-${VERSION_CODENAME}}")
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${codename} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get -qq update
  sudo apt-get -qq install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
else
  echo "   ya instalado: $(docker --version)"
fi

# Asegurar usuario en grupo docker
if ! groups "${USER}" | grep -q '\bdocker\b'; then
  sudo usermod -aG docker "${USER}"
  echo "   ⚠️ ${USER} agregado al grupo docker. Aplicará en próxima sesión SSH."
  echo "      Para este script usaremos sudo en los comandos docker."
  USE_SUDO_DOCKER=1
else
  USE_SUDO_DOCKER=0
fi

# Verificar daemon
${USE_SUDO_DOCKER:+sudo} docker version >/dev/null 2>&1 \
  || { sudo systemctl enable --now docker; sleep 2; }
echo "   docker daemon: activo ✅"
echo "   compose:       $(${USE_SUDO_DOCKER:+sudo} docker compose version | head -1)"

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 3. DNS para containers: dnscrypt-proxy en bridge Docker"
# ────────────────────────────────────────────────────────────────────
DNSCRYPT_TOML=/opt/dnscrypt-proxy/dnscrypt-proxy.toml
if ! sudo grep -q "'${DOCKER_BRIDGE_IP}:${DOH_PORT}'" "${DNSCRYPT_TOML}" 2>/dev/null; then
  echo "   agregando ${DOCKER_BRIDGE_IP}:${DOH_PORT} a listen_addresses..."
  sudo sed -i \
    "s|^listen_addresses = \['127.0.0.1:${DOH_PORT}'\]|listen_addresses = ['127.0.0.1:${DOH_PORT}', '${DOCKER_BRIDGE_IP}:${DOH_PORT}']|" \
    "${DNSCRYPT_TOML}"
  sudo systemctl restart dnscrypt-proxy
  sleep 2
fi
sudo systemctl is-active --quiet dnscrypt-proxy \
  && echo "   dnscrypt-proxy escuchando en 127.0.0.1 y ${DOCKER_BRIDGE_IP} ✅" \
  || { echo "❌ dnscrypt-proxy no activo"; sudo journalctl -u dnscrypt-proxy -n 15 --no-pager; exit 1; }

# Configurar Docker daemon para usar dnscrypt como DNS
DOCKER_DAEMON=/etc/docker/daemon.json
if ! sudo test -f "${DOCKER_DAEMON}" || ! sudo grep -q "${DOCKER_BRIDGE_IP}" "${DOCKER_DAEMON}" 2>/dev/null; then
  echo "   configurando /etc/docker/daemon.json (DNS → ${DOCKER_BRIDGE_IP}:${DOH_PORT})..."
  sudo mkdir -p /etc/docker
  # NOTA: Docker requiere puerto 53 estándar. Usamos iptables redirect 53→5053
  # para que los containers usen :53 y el host redirija al dnscrypt en :5053.
  sudo tee "${DOCKER_DAEMON}" >/dev/null <<EOF
{
  "dns": ["${DOCKER_BRIDGE_IP}"]
}
EOF
  # Redirigir puerto 53 → 5053 en el bridge docker
  if ! sudo iptables -t nat -C PREROUTING -i docker0 -p udp --dport 53 -j REDIRECT --to-ports ${DOH_PORT} 2>/dev/null; then
    sudo iptables -t nat -A PREROUTING -i docker0 -p udp --dport 53 -j REDIRECT --to-ports ${DOH_PORT}
    sudo iptables -t nat -A PREROUTING -i docker0 -p tcp --dport 53 -j REDIRECT --to-ports ${DOH_PORT}
  fi
  # Persistir reglas iptables (apt install iptables-persistent si no está)
  if ! command -v netfilter-persistent >/dev/null; then
    sudo DEBIAN_FRONTEND=noninteractive apt-get -qq install -y iptables-persistent >/dev/null 2>&1 || true
  fi
  command -v netfilter-persistent >/dev/null \
    && sudo netfilter-persistent save >/dev/null 2>&1 || true
  sudo systemctl restart docker
  sleep 3
fi

# Test DNS dentro de container
echo "   probando DNS desde container..."
${USE_SUDO_DOCKER:+sudo} docker run --rm alpine:3.20 sh -c "wget -q -O- https://www.datos.gov.co/api/views.json?limit=1 2>&1 | head -c 80" >/dev/null \
  && echo "   DNS en container: OK ✅" \
  || { echo "❌ DNS en container falla. Diagnóstico abajo:"; ${USE_SUDO_DOCKER:+sudo} docker run --rm alpine:3.20 sh -c "nslookup github.com; echo ---; wget -O- https://github.com 2>&1 | head"; exit 1; }

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 4. Ollama (host)"
# ────────────────────────────────────────────────────────────────────
if ! command -v ollama >/dev/null; then
  echo "   instalando Ollama oficial..."
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Configurar Ollama para escuchar en 0.0.0.0 (para que containers lo alcancen)
DROP_IN=/etc/systemd/system/ollama.service.d/host.conf
if ! sudo test -f "${DROP_IN}"; then
  echo "   configurando Ollama → OLLAMA_HOST=0.0.0.0:11434..."
  sudo mkdir -p /etc/systemd/system/ollama.service.d
  sudo tee "${DROP_IN}" >/dev/null <<'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF
  sudo systemctl daemon-reload
  sudo systemctl restart ollama
  sleep 3
fi

sudo systemctl enable --now ollama
sleep 2
curl -s --max-time 5 http://localhost:11434/api/tags >/dev/null \
  || { echo "❌ Ollama no responde"; exit 1; }
echo "   ollama service: activo en 0.0.0.0:11434 ✅"

# Descargar Qwen 3B
if ! ollama list 2>/dev/null | grep -q "^${OLLAMA_MODEL}"; then
  echo "   descargando ${OLLAMA_MODEL} (~2 GB, puede tardar)..."
  ollama pull "${OLLAMA_MODEL}"
fi
echo "   modelo ${OLLAMA_MODEL} listo ✅"

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 5. Repositorio DatosVivos"
# ────────────────────────────────────────────────────────────────────
if [[ -d "${REPO_DIR}/.git" ]]; then
  echo "   pulling develop..."
  cd "${REPO_DIR}"
  git fetch --all --quiet
  git checkout develop
  git pull --ff-only origin develop
else
  echo "   clonando..."
  git clone --branch develop "${REPO_URL}" "${REPO_DIR}"
  cd "${REPO_DIR}"
fi
echo "   HEAD: $(git log -1 --oneline)"

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 6. .env de producción"
# ────────────────────────────────────────────────────────────────────
if [[ ! -f "${REPO_DIR}/.env" ]]; then
  cat > "${REPO_DIR}/.env" <<EOF
# DatosVivos — Beta-1 producción.
# Generado por scripts/deploy_vm.sh.

# Ollama: en host, accesible via bridge docker
OLLAMA_HOST=http://${DOCKER_BRIDGE_IP}:11434
OLLAMA_BASE_URL=http://${DOCKER_BRIDGE_IP}:11434
OLLAMA_MODEL=${OLLAMA_MODEL}
OLLAMA_FALLBACK_MODEL=

LLM_BACKEND=ollama

# Socrata
SOCRATA_DOMAIN=www.datos.gov.co
SOCRATA_APP_TOKEN=
DISCOVERY_API_URL=https://api.us.socrata.com/api/catalog/v1

# Streamlit
STREAMLIT_PORT=8501
STREAMLIT_THEME=dark

# MCP
MCP_TRANSPORT=sse
MCP_PORT=3000

# App
APP_ENV=production
LOG_LEVEL=INFO
VECTOR_STORE=chromadb
INDEX_PATH=./data/vector_index
EOF
  echo "   .env generado ✅"
else
  echo "   .env ya existe ✅ (no se sobrescribe)"
fi

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 7. Índice vectorial (vía container streamlit, ~10 min)"
# ────────────────────────────────────────────────────────────────────
# Reset de data/ si tiene ownership de root (de un build viejo donde el container
# corría como root). El nuevo Dockerfile usa appuser con UID/GID del host.
if [[ -d "${REPO_DIR}/data/vector_index" ]] && \
   [[ "$(stat -c '%U' "${REPO_DIR}/data/vector_index" 2>/dev/null)" != "${USER}" ]]; then
  echo "   limpiando data/ con ownership viejo de root..."
  sudo rm -rf "${REPO_DIR}/data/vector_index"
fi
mkdir -p "${REPO_DIR}/data"
sudo chown -R "${USER}:${USER}" "${REPO_DIR}/data" 2>/dev/null || true

if [[ -d "${REPO_DIR}/data/vector_index" ]] && [[ "$(find "${REPO_DIR}/data/vector_index" -name 'chroma*' 2>/dev/null | wc -l)" -gt 0 ]]; then
  echo "   índice ya existe ✅ (saltando build)"
else
  echo "   construyendo imagen streamlit (build) con APP_UID=${APP_UID} — puede tardar 5 min..."
  cd "${REPO_DIR}"
  ${USE_SUDO_DOCKER:+sudo} APP_UID=${APP_UID} APP_GID=${APP_GID} \
    docker compose build \
      --build-arg APP_UID=${APP_UID} \
      --build-arg APP_GID=${APP_GID} \
      streamlit 2>&1 | tail -5

  echo "   lanzando build_index en container (background)..."
  ${USE_SUDO_DOCKER:+sudo} APP_UID=${APP_UID} APP_GID=${APP_GID} \
    docker compose run --rm --no-deps \
      --entrypoint "" \
      streamlit \
      python -m scripts.build_index > "${LOG_DIR}/build_index.log" 2>&1 &
  BUILD_PID=$!
  echo "   PID=${BUILD_PID}, log en ${LOG_DIR}/build_index.log"
  echo "   seguir progreso con: tail -f ${LOG_DIR}/build_index.log"
fi

# ────────────────────────────────────────────────────────────────────
echo ""
echo "==> 8. Levantar servicios mcp-server + streamlit"
# ────────────────────────────────────────────────────────────────────
echo "   (esperaremos a que termine el índice antes de iniciar streamlit)"
echo "   por ahora levantamos mcp-server..."
${USE_SUDO_DOCKER:+sudo} APP_UID=${APP_UID} APP_GID=${APP_GID} \
  docker compose build \
    --build-arg APP_UID=${APP_UID} \
    --build-arg APP_GID=${APP_GID} \
    mcp-server 2>&1 | tail -3
${USE_SUDO_DOCKER:+sudo} APP_UID=${APP_UID} APP_GID=${APP_GID} \
  docker compose up -d mcp-server
sleep 5
${USE_SUDO_DOCKER:+sudo} docker compose ps

echo ""
echo "🎉 Deploy parcial completo. Estado:"
echo "   • Docker + Compose:    instalados ✅"
echo "   • DNS containers (DoH): configurado ✅"
echo "   • Ollama (host):       activo en :11434, modelo ${OLLAMA_MODEL} listo"
echo "   • mcp-server (docker): up"
echo "   • Streamlit:           pendiente (esperar índice)"
echo ""
echo "Próximos pasos:"
echo "   1. Esperar a que termine build_index (~10 min):"
echo "        tail -f ${LOG_DIR}/build_index.log"
echo "      → cuando veas '✅ Índice construido' está listo."
echo "   2. Iniciar Streamlit:"
echo "        cd ${REPO_DIR} && ${USE_SUDO_DOCKER:+sudo }docker compose up -d streamlit"
echo "        curl -I http://127.0.0.1:8501/"
echo "   3. Levantar Cloudflare Tunnel (acceso público):"
echo "        bash scripts/setup_cloudflare_tunnel.sh    # próximo script"
