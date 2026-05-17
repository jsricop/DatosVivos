# ADR-001: Ollama local en vez de API externa

**Estado:** Aceptada
**Fecha:** Sprint 1

## Decisión

Servir el LLM localmente con **Ollama** (Qwen 2.5 Coder, default 3B con upgrade a 7B documentado), no a través de una API cloud (Anthropic / OpenAI / Google).

## Razón

- **Soberanía del dato.** Las consultas ciudadanas pueden contener información sensible sobre intereses, regiones, temas — no deben filtrarse a proveedores extranjeros por defecto.
- **Independencia de terceros.** Cualquier corte de servicio, cambio de pricing o política de un proveedor cloud no detiene a DatosVivos.
- **Criterio MinTIC.** Pesa positivamente en evaluación de soberanía técnica.

## Trade-off

- **Calidad narrativa menor** que Claude 4 o GPT-4o. Qwen 3B genera frases más mecánicas y ocasionalmente comete errores que un modelo grande no cometería.
- **Mitigación:** abstraemos el backend con un Protocol (`ai_engine/llm_backend.py`) que soporta `ollama`, `anthropic`, `mock`. Cualquier entidad que prefiera cloud puede activarlo con `LLM_BACKEND=anthropic` sin tocar código.

## Referencias

- `ai_engine/llm_backend.py`
- [`docs/crisp_mlq/04_modeling.md`](../crisp_mlq/04_modeling.md)
