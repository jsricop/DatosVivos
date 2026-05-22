#!/usr/bin/env bash
# scripts/setup_ollama_concurrent.sh
#
# Configura Ollama para concurrencia + keep-alive vía drop-in systemd unit.
# Ejecutar con sudo: `sudo bash scripts/setup_ollama_concurrent.sh`
#
# Settings:
#   OLLAMA_NUM_PARALLEL=2       — 2 queries simultáneas por modelo
#   OLLAMA_KEEP_ALIVE=24h       — modelos quedan cargados 24h sin tráfico
#   OLLAMA_MAX_LOADED_MODELS=2  — coder:3b + qwen:7b ambos cached
#
# Reversible: borrar el drop-in y restart ollama.

set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Este script requiere sudo. Ejecutar: sudo bash $0"
  exit 1
fi

DROPIN_DIR="/etc/systemd/system/ollama.service.d"
DROPIN_FILE="${DROPIN_DIR}/concurrent.conf"

echo "=> Creando drop-in en ${DROPIN_FILE}"
mkdir -p "${DROPIN_DIR}"
cat > "${DROPIN_FILE}" <<'EOF'
# DatosVivos: concurrencia + keep-alive (PROD_IMPROV concurrency 2026-05-22).
# Doc: docs/deployment_runbook.md §Ollama concurrent.
[Service]
Environment="OLLAMA_NUM_PARALLEL=2"
Environment="OLLAMA_KEEP_ALIVE=24h"
Environment="OLLAMA_MAX_LOADED_MODELS=2"
EOF

echo "=> systemctl daemon-reload"
systemctl daemon-reload

echo "=> systemctl restart ollama"
systemctl restart ollama
sleep 3

echo ""
echo "=> Estado del servicio:"
systemctl status ollama --no-pager | head -10

echo ""
echo "=> Verificar env vars cargadas:"
systemctl show ollama -p Environment | tr ' ' '\n' | grep -E "OLLAMA_(NUM_PARALLEL|KEEP_ALIVE|MAX_LOADED)" || true

echo ""
echo "✓ Listo. Para revertir: rm ${DROPIN_FILE} && systemctl daemon-reload && systemctl restart ollama"
