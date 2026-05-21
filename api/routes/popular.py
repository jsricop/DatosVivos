"""GET /api/v1/popular — top consultas leídas de la telemetría CSV.

Si no hay CSV de telemetría aún (deploy fresco), devolvemos lista vacía.
Nunca inventamos. Si el frontend recibe vacío, muestra mensaje de "Aún no
hay consultas suficientes" como define BRAND.md §1.

El CSV puede crecer; usamos un agregado eficiente en memoria limitado a las
últimas 5 000 filas para evitar leer archivos de log enormes.
"""

from __future__ import annotations

import csv
import logging
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Query

import ai_engine.telemetry as telemetry
from api.models.schemas import PopularQuery

router = APIRouter()
log = logging.getLogger(__name__)

_MAX_ROWS = 5_000


@router.get("/popular")
async def popular(
    limit: int = Query(default=7, ge=1, le=50),
) -> dict[str, list[PopularQuery]]:
    path: Path = telemetry.TELEMETRY_PATH
    if not path.exists():
        return {"popular": []}

    questions: Counter[str] = Counter()
    intent_by_question: dict[str, str] = {}

    try:
        with path.open("r", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            rows = list(reader)
    except OSError as exc:
        log.warning("No pude leer telemetría %s: %s", path, exc)
        return {"popular": []}

    for record in rows[-_MAX_ROWS:]:
        q = (record.get("question") or "").strip()
        if not q:
            continue
        questions[q] += 1
        if q not in intent_by_question:
            intent_by_question[q] = (record.get("intent") or "").strip() or "search"

    top = questions.most_common(limit)
    return {
        "popular": [
            PopularQuery(
                question=question,
                count=count,
                intent=intent_by_question.get(question) or None,  # type: ignore[arg-type]
            )
            for question, count in top
        ]
    }
