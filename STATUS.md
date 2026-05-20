# STATUS — DatosVivos

> Estado al cierre de la sesión del 2026-05-20. Sirve como punto de retoma operativo.
> Para detalles de despliegue ver [`docs/deployment_runbook.md`](docs/deployment_runbook.md).

## TL;DR

**Beta-1 desplegado en VM ANI**, accesible vía túnel SSH local. Esperando apertura de TCP/7844 saliente para exponer públicamente vía Cloudflare Tunnel.

## Estado actual del despliegue

### En la VM ANI

| Componente | Estado | Detalle |
|---|---|---|
| `dnscrypt-proxy` (DoH local) | ✅ activo | Resuelve DNS público vía Cloudflare/Google/Quad9 sobre TCP/443 |
| `ollama` (Qwen 2.5 Coder 3B) | ✅ activo | En `:11434`, ~2 GB modelo descargado |
| `docker` engine | ✅ activo | Compose v2 instalado |
| `datosvivos-mcp-server-1` | ✅ Up | Container MCP en `:3000` |
| `datosvivos-streamlit-1` | ✅ Up | Container UI en `:8501` (con `PYTHONPATH=/app` aplicado) |
| `datosvivos-tunnel` (Cloudflare) | ⚠️ activo pero **HTTP 530** | TCP/7844 saliente bloqueado — ver pendientes |
| Índice vectorial | ✅ 8 395 datasets indexados | Backup en `~/vector_index_backup_*.tar.gz` |

### En tu Mac local

| Componente | Estado |
|---|---|
| VPN FortiClient | requiere reconectar al iniciar sesión |
| SSH ControlMaster (`datosvivos`) | configurado en `~/.ssh/config` |
| Port-forward SSH `localhost:8501 → VM:8501` | activo en background (PID variable) |

## Pendientes priorizados para retomar

### 🔴 Bloqueador externo — esperar respuesta de infra

1. **Ticket TCP/7844 saliente** abierto en mesa de ayuda ANI (texto en `/tmp/ticket_infra_7844.md` localmente, también enviado por chat).
   - Sin esto: la URL pública `*.trycloudflare.com` da HTTP 530.
   - Con esto: URL pública con TLS válida para jurado / demos.
   - ETA estimado: 1-2 días.

### 🟡 Pendientes que podemos hacer sin esperar a infra

2. **Re-correr el journey de 30 preguntas en la VM** (el último intento se detuvo prematuramente). Confirma que el deploy producción da las mismas métricas que el entorno local.
3. **Probar manualmente la UI** (`http://localhost:8501` vía túnel SSH) con 5-10 preguntas reales para validación cualitativa antes del jurado.
4. **(Opcional) Considerar ngrok free** como workaround para una URL pública temporal mientras llega TCP/7844, sabiendo que tiene pantalla intersticial inadecuada para jurado.
5. **(Opcional) Comprar dominio Cloudflare** (~USD 10/año) para preparar Named Tunnel con URL fija cuando se autorice 7844.

### 🟢 Mejoras post-Beta-1 (roadmap completo en `docs/PROD_IMPROV.md`)

- Cobertura completa de mpios DIVIPOLA (~1 100 vs 39 actuales).
- Detección de comparativa implícita ("qué departamento tiene más X").
- Validación geográfica de rows (anti-atribución incorrecta).
- Migración LLM 3B → 7B en producción cuando hardware lo permita.
- Cache local de datasets (post 2-4 semanas de telemetría).

## Para retomar mañana — comandos exactos

### 1. Reconectar a la VM

```bash
# En tu Mac
# 1.1 Conectar VPN FortiClient (manual desde la app)
# 1.2 Abrir SSH ControlMaster
ssh datosvivos
# (te pide password una vez; queda persistente 4h)

# Verificar que el master quedó activo
ssh -O check datosvivos       # → "Master running (pid=...)"

# 1.3 Reabrir port-forward SSH para ver UI en tu Mac (si no quedó activo)
ssh -L 8501:localhost:8501 datosvivos -N -f
```

### 2. Re-attach a tmux

```bash
ssh datosvivos
tmux ls                                 # listar sesiones
tmux attach -t datosvivos               # entrar a la sesión que dejaste anoche
```

### 3. Verificar salud del sistema

```bash
# Dentro de la sesión SSH
systemctl is-active dnscrypt-proxy ollama docker datosvivos-tunnel
cd ~/DatosVivos && sudo docker compose ps
curl -I http://localhost:8501/          # debe responder HTTP 200
```

### 4. Abrir UI en navegador

```
http://localhost:8501
```

(Requiere port-forward SSH activo del paso 1.3.)

### 5. Si llega la apertura de TCP/7844

```bash
# En la VM, reiniciar el tunnel y obtener URL pública
sudo systemctl restart datosvivos-tunnel
sleep 10
sudo journalctl -u datosvivos-tunnel -n 200 --no-pager | grep trycloudflare | head -1
```

## Procesos relevantes corriendo

| Servicio | Tipo | Comando ver logs |
|---|---|---|
| dnscrypt-proxy | systemd | `sudo journalctl -u dnscrypt-proxy -f` |
| ollama | systemd | `sudo journalctl -u ollama -f` |
| datosvivos-tunnel | systemd | `sudo journalctl -u datosvivos-tunnel -f` |
| mcp-server container | docker | `sudo docker compose logs -f mcp-server` |
| streamlit container | docker | `sudo docker compose logs -f streamlit` |

## Commits del día (referencia)

| SHA | Resumen |
|---|---|
| `4aaecae`..`2a8aa46` (6) | Sprint 6 — cifras pandas + GeoResolver + comparativa + telemetría + journey ampliado |
| `46c13ee` | Iter1 — plantillas SoQL columna-nombre + sinónimo ciudades |
| `eadab82` | Iter2 — rerank 'NINGUNO' conserva top-1 |
| `a470403` | Docs Sprint 6 — CHANGELOG, README, CRISP-ML(Q), ADRs |
| `6f056ff` | Script exploratory session |
| `9aed82e` | Scripts deploy_vm + setup_doh_vm (con info infra que después se limpió) |
| `0741b1d` | Fix Docker: appuser no-root con UID/GID host |
| `aca60b1` | Limpieza datos infra del HEAD |
| `67fadfc` | Scripts fix_docker_dns + setup_cloudflare_tunnel |
| `6eb8028` | Runbook deployment |
| `a229bc1` | Fix PYTHONPATH=/app en docker-compose |

## Archivos clave generados hoy

| Archivo | Para qué |
|---|---|
| `scripts/setup_doh_vm.sh` | Configura DoH para entornos con DNS interno restringido |
| `scripts/deploy_vm.sh` | Deploy producción end-to-end |
| `scripts/fix_docker_dns.sh` | DNS para containers Docker (cuando daemon.json no resuelve) |
| `scripts/setup_cloudflare_tunnel.sh` | Levanta Cloudflare Quick Tunnel |
| `docs/deployment_runbook.md` | Runbook completo de operación |
| `docs/PROD_IMPROV.md` | Roadmap post-Beta-1 |
| `/tmp/ticket_infra_7844.md` (no commiteado) | Texto para mesa de ayuda |

## Cierre

Beta-1 está **operativa en la VM** y accesible internamente vía VPN + tunnel SSH. La exposición pública depende de un único bloqueador externo (TCP/7844). El código no requiere más trabajo crítico para esta fase; cualquier mejora adicional cae en `docs/PROD_IMPROV.md`.
