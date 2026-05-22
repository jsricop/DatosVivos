"""DashboardSpecGenerator — razona con un LLM qué visualizaciones tienen sentido
para una pregunta + rows reales, y emite un DashboardSpec validado (PLAN_DASHBOARD §4).

Diseño:
- Recibe `LLMBackend` por inyección (default operativo `qwen2.5-coder:7b-instruct-q4_K_M`
  via env `OLLAMA_MODEL`; tests usan MockBackend).
- Llama al LLM con un prompt estructurado (`ai_engine/prompts/dashboard_spec.md`).
- Valida el JSON con Pydantic.
- Si el JSON falla la primera vez, reintenta una vez con instrucción de "JSON estricto".
- Descarta blocks que referencien columnas inexistentes (alucinación) sin abortar todo el spec.
- Devuelve `None` cuando:
    * rows está vacío,
    * el LLM falla 2 veces,
    * no queda ningún block válido tras el filtro.

Sin acoplamiento con `Analyzer` — se llama desde `api/routes/query.py` después de
que `Analyzer.analyze()` devolvió rows + stats.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ai_engine.geo_resolver import GeoContext
from ai_engine.llm_backend import LLMBackend
from ai_engine.stats_computer import Statistics
from api.models.dashboard import (
    ChartBlock,
    DashboardSpec,
    MapBlock,
    TableBlock,
)

log = logging.getLogger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "dashboard_spec.md"
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


class DashboardSpecGenerator:
    """Razona con un LLM qué dashboard renderizar dada la pregunta + rows."""

    def __init__(self, llm: LLMBackend, *, max_retries: int = 1) -> None:
        self.llm = llm
        self.max_retries = max_retries
        self._prompt_template = self._load_prompt()

    # --- public API ---

    async def generate(
        self,
        *,
        question: str,
        intent: str,
        dataset_name: str,
        columns: list[str],
        rows: list[dict[str, Any]],
        stats: Statistics | None = None,
        geo_ctx: GeoContext | None = None,
    ) -> DashboardSpec | None:
        """Emite un DashboardSpec o devuelve None si no aplica."""
        if not rows:
            return None
        if not columns:
            columns = list(rows[0].keys())

        prompt = self._render_prompt(
            question=question,
            intent=intent,
            dataset_name=dataset_name,
            columns=columns,
            rows=rows,
            stats=stats,
            geo_ctx=geo_ctx,
        )

        spec = await self._ask_and_parse(prompt)
        if spec is None and self.max_retries > 0:
            spec = await self._ask_and_parse(
                prompt
                + "\n\nIMPORTANTE: devolvé EXCLUSIVAMENTE JSON válido, sin texto adicional.",
            )
        if spec is None:
            return None

        valid_blocks = _filter_blocks_with_existing_columns(spec, set(columns))
        if not valid_blocks:
            log.info("DashboardSpec descartado: 0 blocks válidos tras filtro de columnas")
            return None
        if len(valid_blocks) != len(spec.blocks):
            # Construir un nuevo spec con solo los blocks válidos.
            return spec.model_copy(update={"blocks": valid_blocks})
        return spec

    # --- internal helpers ---

    async def _ask_and_parse(self, prompt: str) -> DashboardSpec | None:
        from ai_engine.llm_backend import model_for_task
        try:
            raw = await self.llm.generate(
                prompt,
                max_tokens=900,
                model=model_for_task("dashboard"),
                temperature=0,
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("DashboardSpec LLM call falló: %s", exc)
            return None
        json_text = _extract_json(raw)
        if not json_text:
            log.info("DashboardSpec: LLM no devolvió JSON parseable")
            return None
        try:
            payload = json.loads(json_text)
        except json.JSONDecodeError as exc:
            log.info("DashboardSpec JSON inválido (%s) — primeros 200 chars: %r", exc, json_text[:200])
            return None
        try:
            return DashboardSpec.model_validate(payload)
        except ValidationError as exc:
            log.info("DashboardSpec validación Pydantic falló: %s", exc)
            return None

    def _render_prompt(
        self,
        *,
        question: str,
        intent: str,
        dataset_name: str,
        columns: list[str],
        rows: list[dict[str, Any]],
        stats: Statistics | None,
        geo_ctx: GeoContext | None,
    ) -> str:
        columns_listing = "\n".join(f"  - {c}" for c in columns)
        rows_preview = json.dumps(rows[:5], ensure_ascii=False, default=str)

        stats_section = ""
        if stats and stats.summary_lines:
            lines = "\n".join(f"  - {line}" for line in stats.summary_lines[:6])
            stats_section = f"STATS (cifras autorizadas, no inventes otras):\n{lines}\n"

        geo_section = ""
        if geo_ctx and geo_ctx.targets:
            geo_targets = ", ".join(
                f"{t.name} ({t.code or 'nacional'})" for t in geo_ctx.targets[:5]
            )
            geo_section = f"GEO_CONTEXT: {geo_targets} (modo: {geo_ctx.comparison_mode or 'simple'})\n"

        return (
            self._prompt_template.replace("{question}", question)
            .replace("{intent}", intent)
            .replace("{dataset_name}", dataset_name)
            .replace("{columns_listing}", columns_listing)
            .replace("{rows_preview}", rows_preview)
            .replace("{stats_section}", stats_section)
            .replace("{geo_section}", geo_section)
        )

    @staticmethod
    def _load_prompt() -> str:
        try:
            return _PROMPT_PATH.read_text(encoding="utf-8")
        except OSError as exc:
            log.warning("Prompt %s no encontrado: %s — uso fallback inline", _PROMPT_PATH, exc)
            return _FALLBACK_PROMPT


def _extract_json(raw: str) -> str | None:
    """Extrae el primer objeto JSON razonable de la salida del LLM.

    Acepta tres formatos:
    - JSON crudo (más común con temperature=0 e instrucción explícita).
    - Bloque ```json ... ``` (Qwen suele rodear así).
    - JSON precedido o seguido por explicación corta (el LLM no respetó la regla).
    """
    if not raw:
        return None
    raw = raw.strip()
    # 1) Fence ```json ... ```
    match = _JSON_FENCE_RE.search(raw)
    if match:
        return match.group(1).strip()
    # 2) Primer { … } balanceado.
    start = raw.find("{")
    if start < 0:
        return None
    depth = 0
    in_str = False
    escaped = False
    for i in range(start, len(raw)):
        ch = raw[i]
        if in_str:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return raw[start : i + 1]
    return None


def _filter_blocks_with_existing_columns(
    spec: DashboardSpec, available: set[str]
) -> list[Any]:
    """Devuelve la sub-lista de blocks cuyos column-refs existen en `available`.

    KPI no se valida contra columns (puede referenciar agregados de stats).
    """
    kept = []
    for block in spec.blocks:
        if isinstance(block, ChartBlock):
            cols = {block.x_column, block.y_column}
            if block.groupby:
                cols.add(block.groupby)
            if not cols.issubset(available):
                continue
        elif isinstance(block, MapBlock):
            if not {block.code_column, block.metric_column}.issubset(available):
                continue
        elif isinstance(block, TableBlock):
            if not set(block.columns).issubset(available):
                continue
        kept.append(block)
    return kept


_FALLBACK_PROMPT = """Eres un diseñador de dashboards de datos abiertos colombianos.
Devolvés un único JSON con el dashboard más útil para la pregunta y los datos
proporcionados. Sin prosa, sin markdown.

PREGUNTA: «{question}»
INTENT: {intent}
DATASET: {dataset_name}

COLUMNAS:
{columns_listing}

PREVIEW:
{rows_preview}

{stats_section}
{geo_section}
"""


__all__ = ["DashboardSpecGenerator"]


# Silenciar "imported but unused" para asyncio (usado por type checkers en el contrato async).
_ = asyncio
