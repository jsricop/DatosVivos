# Runbook de despliegue — DatosVivos Beta-1

> Documento operativo capturando todo lo aprendido al desplegar DatosVivos en una VM corporativa con red restringida. Sirve como referencia para replicar el despliegue en otra VM, recuperar de fallas, o entender el "por qué" de cada decisión.
>
> **Audiencia:** equipo técnico de DatosVivos. Estilo conciso, pragmático.
>
> Última actualización: 2026-05-20.

## TL;DR — orden de ejecución end-to-end

Para un despliegue limpio desde cero en una VM Ubuntu con `python3.12`, `git` y `curl` preinstalados:

```bash
# Paso 1 (host): configurar SSH ControlMaster — ver MAIN.md §5.0.1
# Paso 2 (VM): instalar DNS-over-HTTPS si los DNS internos no resuelven externos
sudo bash scripts/setup_doh_vm.sh

# Paso 3 (VM): instalar Docker, Ollama, repo, .env, índice vectorial, mcp-server
bash scripts/deploy_vm.sh

# Paso 4 (VM): si DNS en containers no funciona, fix
sudo bash scripts/fix_docker_dns.sh

# Paso 5 (VM): levantar Streamlit (después de que termine el build_index)
cd ~/DatosVivos
sudo docker compose up -d streamlit

# Paso 6 (VM): exponer públicamente (requiere TCP/7844 saliente autorizado)
sudo bash scripts/setup_cloudflare_tunnel.sh
```

## Prerrequisitos en la VM

| Recurso | Mínimo | Recomendado |
|---|---|---|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 16 GB | 32 GB (Ollama 3B Q4 usa ~2.5 GB) |
| Disco libre | 10 GB | 20+ GB (Docker imágenes ~3 GB, Ollama 2 GB, índice 50 MB, modelo embeddings 1 GB) |
| Sistema | Ubuntu 22.04+ | Ubuntu 24.04 LTS |
| Python | 3.11 | 3.12 |
| Conectividad | TCP/443 saliente | + TCP/7844 (Cloudflare Tunnel) |

## Decisiones de red corporativa (el caso ANI)

La VM de ANI tiene una postura de red **restrictiva-pero-funcional**: solo TCP/443 saliente autorizado a internet. Esto rompe los siguientes flujos default:

| Default | Restricción ANI | Solución aplicada |
|---|---|---|
| DNS por UDP/53 a resolvers públicos | UDP/53 bloqueado | dnscrypt-proxy local con DoH (TCP/443) |
| `apt install` desde repositorios oficiales | TCP/443 autorizado a esos dominios | OK directo (whitelist incluye archive.ubuntu.com) |
| Docker containers DNS | Containers no heredan DoH del host | dnscrypt en `172.17.0.1:53`, daemon.json con esa IP |
| Cloudflare Tunnel | Requiere TCP/7844 (no 443) | Pedir apertura adicional; mientras tanto ngrok |

Esto es **común en entornos gubernamentales** — replicar el setup en otra VM ANI requiere los mismos workarounds.

## Comandos clave por escenario

### Conectarme y operar la VM

```bash
# Asumiendo VPN FortiClient activa y ~/.ssh/config configurado (ver MAIN.md §5.0.1)
ssh datosvivos                          # abrir sesión master (1 sola vez por sesión)
ssh -O check datosvivos                 # verificar master activo
ssh datosvivos 'comando'                # ejecutar comando sin reabrir sesión
ssh -L 8501:localhost:8501 datosvivos -N -f   # túnel para ver UI en tu Mac
```

### Sesiones persistentes con tmux

```bash
# Crear (primera vez)
TERM=xterm-256color tmux new -s datosvivos
# Detach sin cerrar (Ctrl+B, D)
# Reattach
tmux attach -t datosvivos
# Listar
tmux ls
```

### Verificar salud del sistema

```bash
ssh datosvivos 'systemctl is-active ollama dnscrypt-proxy docker datosvivos-tunnel'
ssh datosvivos 'cd ~/DatosVivos && sudo docker compose ps'
curl -I http://localhost:8501/        # vía túnel SSH local
```

### Reconstruir el índice vectorial (~10 min)

```bash
ssh datosvivos 'cd ~/DatosVivos && sudo docker compose run --rm --no-deps \
  --entrypoint "" streamlit python -m scripts.build_index 2>&1 \
  | tee ~/datosvivos-logs/build_index_$(date +%Y%m%d).log'
```

### Restaurar el índice desde backup

```bash
ssh datosvivos 'cd ~/DatosVivos && rm -rf data/vector_index && \
  tar xzf ~/vector_index_backup_YYYYMMDD_HHMM.tar.gz -C data/'
```

### Backup del índice

```bash
ssh datosvivos 'cd ~/DatosVivos && tar czf ~/vector_index_backup_$(date +%Y%m%d_%H%M).tar.gz -C data vector_index/'
```

### Re-deploy completo (preserva datos)

```bash
ssh datosvivos 'cd ~/DatosVivos && git pull origin develop && \
  sudo docker compose build && \
  sudo docker compose up -d'
```

## Troubleshooting

### "DNS no resuelve" en containers

```bash
# Verificar dnscrypt-proxy escuchando en 172.17.0.1:53
ss -tlnp 2>/dev/null | grep "172.17.0.1:53"

# Verificar docker daemon.json
cat /etc/docker/daemon.json

# Test directo
sudo docker run --rm alpine:3.20 nslookup github.com

# Si falla, re-ejecutar:
sudo bash scripts/fix_docker_dns.sh
```

### "Permission denied" escribiendo a `data/vector_index`

```bash
# Causa: ownership mal en un build anterior con USER root
sudo chown -R $(id -u):$(id -g) ~/DatosVivos/data/
```

### "HTTP 530" desde URL pública de Cloudflare Tunnel

```bash
# Causa habitual: cloudflared no puede conectar al edge por TCP/7844
sudo journalctl -u datosvivos-tunnel -n 30 --no-pager | grep -iE "error|fatal"

# Si dice "i/o timeout dial tcp ...:7844", pedir a infra apertura TCP/7844 saliente.
```

### "Streamlit no responde"

```bash
# Verificar logs del container
sudo docker compose logs --tail=50 streamlit

# Reiniciar
sudo docker compose restart streamlit

# Si persiste, rebuild
sudo docker compose down streamlit && sudo docker compose up -d streamlit
```

### Cloudflare Tunnel asignó nueva URL (random)

```bash
# Esperado al reiniciar — Quick Tunnels no tienen URL fija.
sudo journalctl -u datosvivos-tunnel -n 200 --no-pager | grep trycloudflare | head -1
```

Para URL fija: comprar dominio + migrar a Named Tunnel (no cubierto aquí).

## Servicios systemd activos en la VM

| Servicio | Función | Activado por |
|---|---|---|
| `ollama` | Servidor LLM local en `:11434` | Instalador oficial Ollama + `scripts/setup_ollama_concurrent.sh` (drop-in concurrencia) |
| `dnscrypt-proxy` | Resolver DoH local | `setup_doh_vm.sh` |
| `docker` | Engine de containers | apt install docker-ce |
| `datosvivos-tunnel` | Cloudflare Tunnel saliente | `setup_cloudflare_tunnel.sh` |

Ver todos: `systemctl list-units --type=service --state=running`.

### Ollama concurrent (drop-in systemd)

Para soportar 2 queries concurrentes y mantener modelos calientes:

```bash
sudo bash scripts/setup_ollama_concurrent.sh
```

Crea `/etc/systemd/system/ollama.service.d/concurrent.conf` con:
- `OLLAMA_NUM_PARALLEL=2` — 2 queries simultáneas por modelo.
- `OLLAMA_KEEP_ALIVE=24h` — modelos cargados 24h sin tráfico (sin cold-start).
- `OLLAMA_MAX_LOADED_MODELS=2` — coder:3b + qwen:7b ambos en RAM.

**RAM extra**: ~10 GB (de 31 GB total VM ANI). Verificado tras deploy: `nvidia-smi` o `free -h`.

**Revertir**: `sudo rm /etc/systemd/system/ollama.service.d/concurrent.conf && sudo systemctl daemon-reload && sudo systemctl restart ollama`.

## Containers Docker

| Container | Imagen | Puerto host | Función |
|---|---|---|---|
| `datosvivos-mcp-server-1` | `datosvivos-mcp-server` | `3000` | MCP SSE server |
| `datosvivos-streamlit-1` | `datosvivos-streamlit` | `8501` | UI Streamlit + motor IA |

## Logs operacionales

| Log | Ubicación |
|---|---|
| build_index | `~/datosvivos-logs/build_index*.log` |
| journey (30 preguntas) | `~/datosvivos-logs/vm_journey*.log` |
| Streamlit container | `sudo docker compose logs streamlit` |
| MCP server container | `sudo docker compose logs mcp-server` |
| Ollama | `sudo journalctl -u ollama -f` |
| Cloudflare Tunnel | `sudo journalctl -u datosvivos-tunnel -f` |
| dnscrypt-proxy | `sudo journalctl -u dnscrypt-proxy -f` |
| Telemetría de consultas | `~/DatosVivos/data/telemetry/queries.csv` (en host, vía volume) |

## Decisiones de diseño documentadas

- [ADR-001 Ollama local](adr/001-ollama-local.md)
- [ADR-005 ChromaDB](adr/005-chromadb-vs-pgvector.md)
- [ADR-009 Cifras pandas + whitelist](adr/009-cifras-pandas-whitelist.md)
- [ADR-010 GeoResolver](adr/010-geo-resolver.md)
- [PROD_IMPROV.md](PROD_IMPROV.md) — roadmap post-Beta-1

## Comandos de emergencia

### "Todo se rompió, quiero empezar de cero (sin perder el repo ni .env)"

```bash
# 1. Parar todo
ssh datosvivos 'cd ~/DatosVivos && sudo docker compose down -v'

# 2. Limpiar imágenes y caches
ssh datosvivos 'sudo docker system prune -af --volumes'

# 3. Re-deploy (idempotente, no re-clona)
ssh datosvivos 'cd ~/DatosVivos && bash ~/deploy_vm.sh'
```

### "Quiero apagar el túnel público inmediatamente"

```bash
ssh datosvivos 'sudo systemctl stop datosvivos-tunnel'
```

Después podés volver a levantarlo con `sudo systemctl start datosvivos-tunnel` o re-correr `setup_cloudflare_tunnel.sh`.
