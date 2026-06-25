"""Verificador de consulta de 3 capas (ADR-022 §1, patrón PV-SQL). Fase 2.

Cierra el hueco crítico: la validación previa solo revisaba los NÚMEROS de la
narrativa, no la CORRECCIÓN de la consulta. Aquí verificamos que el SoQL generado
realmente responde la pregunta, antes de afirmar la cifra.

Capas:
  1. Sintaxis (pura, sin ejecutar): SELECT, sin FROM (SoQL), paréntesis balanceados,
     columnas ⊆ esquema real, GROUP BY coherente.
  2. Ejecución barata (`verify_execution`, async): `SELECT … LIMIT 0` contra SODA
     (SoQL no tiene EXPLAIN). Captura el 400 de Socrata sin traer datos.
  3. Restricciones semánticas (pura): el SoQL cumple la intención de la pregunta
     (QueryConstraints) contra los `semantic_type` de las columnas curadas.

`verify_static` corre capas 1 y 3 (sin IO) — la usa el bucle de reparación (Fase 3).
`verify_execution` corre la capa 2 (async) — una sola vez antes de la ejecución real.
Los mensajes de error son DIRIGIDOS (para reparación, no genéricos).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Literal

from ai_engine.query_constraints import QueryConstraints
from ai_engine.query_generator import _extract_referenced_columns

Layer = Literal["syntax", "execution", "semantic"]

_AGG_RE = re.compile(r"\b(count|sum|avg|min|max)\s*\(", re.IGNORECASE)
_GROUPBY_RE = re.compile(r"\bgroup\s+by\b(.*?)(?:\border\s+by\b|\blimit\b|$)", re.IGNORECASE | re.DOTALL)
_SELECT_RE = re.compile(r"^\s*select\b(.*?)(?:\bwhere\b|\bgroup\s+by\b|\border\s+by\b|\blimit\b|$)",
                        re.IGNORECASE | re.DOTALL)
_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")


@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    layer_failed: Layer | None
    error_message: str
    columns_referenced: frozenset[str]

    @staticmethod
    def passed(cols: frozenset[str]) -> "VerificationResult":
        return VerificationResult(True, None, "", cols)


def _semantic_map(curated_columns: list[dict[str, Any]]) -> dict[str, str]:
    """{col_name.lower(): semantic_type} desde las columnas curadas."""
    out: dict[str, str] = {}
    for c in curated_columns or []:
        name = (c.get("col_name") or "").lower()
        st = c.get("semantic_type")
        if name and st:
            out[name] = st
    return out


def _groupby_columns(soql: str) -> set[str]:
    m = _GROUPBY_RE.search(soql)
    if not m:
        return set()
    return {t.lower() for t in _IDENT_RE.findall(m.group(1))}


def _select_columns(soql: str) -> list[str]:
    """Items de la lista SELECT (texto crudo de cada uno, separados por coma de tope)."""
    m = _SELECT_RE.search(soql)
    if not m:
        return []
    body = m.group(1)
    # split por comas de nivel 0 (ignora comas dentro de paréntesis)
    items, depth, cur = [], 0, ""
    for ch in body:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(cur.strip())
    return items


def _bare_select_columns(soql: str) -> set[str]:
    """Columnas no-agregadas del SELECT (las que deben ir en GROUP BY)."""
    out: set[str] = set()
    for item in _select_columns(soql):
        if _AGG_RE.search(item):
            continue  # agregado: no exige GROUP BY
        # quitar alias `... AS x`
        item = re.sub(r"\bas\s+[a-zA-Z_][a-zA-Z0-9_]*", "", item, flags=re.IGNORECASE)
        idents = _IDENT_RE.findall(item)
        if idents:
            out.add(idents[0].lower())
    return out


def verify_static(
    soql: str,
    *,
    valid_cols: set[str],
    curated_columns: list[dict[str, Any]],
    constraints: QueryConstraints,
    dialect: Literal["soql", "duckdb"] = "soql",
) -> VerificationResult:
    """Capas 1 (sintaxis) y 3 (restricciones semánticas). Pura, sin IO."""
    s = (soql or "").strip()
    referenced = frozenset(_extract_referenced_columns(s))

    # ---------- Capa 1: sintaxis ----------
    if not s:
        return VerificationResult(False, "syntax", "El SoQL está vacío.", referenced)
    if not re.match(r"^\s*select\b", s, re.IGNORECASE):
        return VerificationResult(False, "syntax", "El SoQL debe empezar con SELECT.", referenced)
    if dialect == "soql" and re.search(r"\bfrom\b", s, re.IGNORECASE):
        return VerificationResult(
            False, "syntax",
            "SoQL no usa FROM (el dataset es el endpoint). Quita la cláusula FROM.",
            referenced,
        )
    if s.count("(") != s.count(")"):
        return VerificationResult(False, "syntax", "Paréntesis desbalanceados en el SoQL.", referenced)

    invalid = referenced - {c.lower() for c in valid_cols} - {"*"}
    if invalid:
        return VerificationResult(
            False, "syntax",
            f"Estas columnas no existen en el dataset: {sorted(invalid)}. "
            f"Usa SOLO las columnas reales del esquema.",
            referenced,
        )

    gb = _groupby_columns(s)
    if gb:
        bare = _bare_select_columns(s)
        missing = bare - gb
        if missing:
            return VerificationResult(
                False, "syntax",
                f"Columnas en SELECT sin agregación deben ir en GROUP BY: {sorted(missing)}.",
                referenced,
            )

    # ---------- Capa 3: restricciones semánticas ----------
    sem = _semantic_map(curated_columns)
    has_lower = s.lower()

    if constraints.requires_count and not _AGG_RE.search(s):
        return VerificationResult(
            False, "semantic",
            "La pregunta pide un conteo/cantidad; tu consulta no agrega. "
            "Usa `count(*) AS n` (o la métrica adecuada).",
            referenced,
        )

    if constraints.requires_orderby_limit and not (
        "order by" in has_lower and "limit" in has_lower
    ):
        return VerificationResult(
            False, "semantic",
            "La pregunta pide un ranking/top; tu consulta debe tener "
            "`ORDER BY <métrica> DESC LIMIT <n>`.",
            referenced,
        )

    if constraints.requires_groupby and not gb:
        return VerificationResult(
            False, "semantic",
            "La pregunta pide desglose/comparación; falta `GROUP BY` sobre la "
            "columna correspondiente.",
            referenced,
        )

    # Tipo semántico esperado: al menos una columna agrupada/usada debe ser del tipo.
    if constraints.expected_semantic_types:
        used = (gb or referenced)
        used_types = {sem.get(c) for c in used if sem.get(c)}
        if not (used_types & set(constraints.expected_semantic_types)):
            want = "/".join(sorted(constraints.expected_semantic_types))
            return VerificationResult(
                False, "semantic",
                f"La pregunta requiere agrupar/usar una columna de tipo «{want}», "
                f"pero la consulta no usa ninguna columna de ese tipo.",
                referenced,
            )

    if constraints.requires_geo_filter:
        geo_cols = {c for c, t in sem.items() if t == "geo"}
        if "where" not in has_lower or not (referenced & geo_cols):
            return VerificationResult(
                False, "semantic",
                "La pregunta es sobre un territorio específico; tu consulta debe "
                "filtrar con `WHERE <columna_geo> = <código>`.",
                referenced,
            )

    return VerificationResult.passed(referenced)


async def verify_execution(
    soql: str,
    *,
    soda_client: Any,
    dataset_id: str,
) -> VerificationResult:
    """Capa 2: ejecuta `LIMIT 0` contra SODA (SoQL no tiene EXPLAIN).

    Devuelve ok=True si Socrata acepta la consulta (sin traer filas). Si responde
    400, captura el mensaje como error dirigido.
    """
    probe = _with_limit_zero(soql)
    try:
        await soda_client.query(dataset_id=dataset_id, soql_query=probe)
        return VerificationResult.passed(frozenset())
    except Exception as exc:  # noqa: BLE001
        msg = str(exc)
        # Acortar mensajes largos de httpx, conservando el detalle de Socrata.
        return VerificationResult(
            False, "execution",
            f"Socrata rechazó la consulta: {msg[:300]}",
            frozenset(),
        )


def _with_limit_zero(soql: str) -> str:
    """Reescribe el LIMIT a 0 (o lo agrega) para validar sin traer datos."""
    s = soql.strip().rstrip(";").strip()
    if re.search(r"\blimit\b", s, re.IGNORECASE):
        return re.sub(r"\blimit\s+\d+\b", "LIMIT 0", s, flags=re.IGNORECASE)
    return f"{s} LIMIT 0"
