# 10 — Acta de cierre del Sprint 5 y del MVP

**Fecha de cierre:** 2026-05-16
**Equipo:** ANI (Agencia Nacional de Infraestructura) — Oficina de Tecnología
**Concurso:** Datos al Ecosistema 2026: IA para Colombia — Reto #07
**Repositorio:** https://github.com/jsricop/DatosVivos
**Licencia:** MIT

## Estado al cierre

| Sprint | Entregable | Estado |
|---|---|---|
| 1 | MCP Server + 3 tools sobre datos.gov.co | ✅ |
| 2 | Motor de IA local (índice vectorial + clasificador) | ✅ |
| 3 | `cross_datasets` + Ollama + analyzer end-to-end | ✅ |
| Extensión | 3-tier search (acrónimos + topic keywords + LLM) | ✅ |
| 4 | UI Streamlit + accesibilidad (sin Power BI) | ✅ |
| 5 | Docs CRISP-ML(Q) + capítulo MCP + checklist MinTIC | ✅ |

## Métricas finales del MVP

| Métrica | Valor |
|---|---|
| Datasets indexados de datos.gov.co | **8 389** |
| Entidades públicas catalogadas | **117** |
| Aliases de acrónimos | **562** |
| Topic keywords | **~3 050** |
| Tools MCP expuestas | **4** |
| Tests automatizados | **82** (suite no-integration) |
| Tests de aceptación congelados por sprint | **4 sprints, 50+ tests** |
| ADRs registrados | **8** (públicos en `docs/adr/`) |
| Documentos CRISP-ML(Q) | **9** + checklist + pitch + acta |
| Lecciones aprendidas documentadas | **10+** |
| Líneas de Python | ~5 000 |
| Líneas de documentación | ~3 500 |

## Cumplimiento de disciplinas adoptadas

- ✅ **Test-first (MAIN.md §6.6):** los criterios de aceptación se congelaron antes de implementar. Solo se ajustaron por errores conceptuales explícitos.
- ✅ **Doc-first (MAIN.md §6.5):** cada PR que afectó arquitectura, scope o decisión documentada actualizó la documentación pública en el mismo PR.
- ✅ **Commit convention:** `tipo(scope): descripción` con `Co-Authored-By: ANI Team & Claude <noreply@anthropic.com>` en todos los commits.
- ✅ **PRs descriptivos:** cada PR enumera scope, archivos cambiados y test plan.

## Pendientes que requieren operación (no del repo)

- 🔜 **Publicación en `datos.gov.co` y `herramientas.datos.gov.co/usos`:** requiere coordinación con MinTIC y acceso del operador al portal.
- 🔜 **Demo público con TLS:** levantar Nginx + Let's Encrypt sobre la VM con un dominio público.
- 🔜 **Pitch / video grabado:** seguir guion en `docs/crisp_mlq/09_pitch_sustentacion.md`.
- 🔜 **Sustentación presencial:** preparar primer semana de agosto si pasamos a finalistas.

## Gaps abiertos honestos (declarados al jurado)

Todos los gaps cerrables localmente se cerraron antes del 2026-05-16. Quedan únicamente:

1. **PostgreSQL logging persistente** — fuera de scope del Sprint 4. Schema definido en `db/init.sql` como referencia. Activable cuando se decida instrumentar telemetría real.
2. **Power BI / dashboards analíticos** — fuera de scope del entregable ([ADR-008](../adr/008-scope-sin-powerbi.md)). Conectable a PostgreSQL cuando se active el logging.
3. **Demo público con TLS** — pendiente publicación.

## Lecciones aprendidas en proceso

- Adoptar **test-first** ahorró tiempo: cuando un test fallaba, sabíamos exactamente qué criterio estaba roto. Sin esto, hubiéramos perseguido bugs que no eran críticos para el objetivo.
- El bug del campo `tags` de Socrata (mal poblado con `columns_field_name`) **no se hubiera detectado sin auditar el catálogo a fondo**. La fase Data Understanding pagó dividendos.
- **El usuario no menciona entidades por nombre** — diseñar 3-tier search desde el inicio hubiera ahorrado un retrabajo de Sprint 2 a Sprint 3. Captured en [ADR-007](../adr/007-busqueda-3-tiers.md).
- **El error operativo del PR #11 a main** (en vez de develop) se corrigió por fast-forward sin pérdida de cambios. Lección: pasar `--base develop` explícito en `gh pr create`. PR #12 ya lo aplica.

## Anexo: cómo el equipo auditor puede verificar todo

```bash
# Clonar y armar entorno
git clone https://github.com/jsricop/DatosVivos
cd DatosVivos
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.mcp.txt -r requirements.ai.txt \
            -r requirements.streamlit.txt -r requirements-dev.txt

# LLM local
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull qwen2.5-coder:3b

# Índice vectorial (~10 min, una sola vez)
python -m scripts.build_index

# Verificar la suite
pytest -m "not integration" -q                # ~30 s
pytest tests/test_sprint4_acceptance.py -q   # 16 verdes
pytest tests/test_sprint3_acceptance.py -q   # 16 verdes (con Ollama)

# Ver la app
streamlit run app/main.py
# → http://localhost:8501

# Integración MCP con Claude Desktop
# Seguir docs/crisp_mlq/07_mcp_integrations.md
```

---

**Firmado:** Oficina de Tecnología, ANI · Mayo 2026.
