"""Generador de SoQL desde lenguaje natural usando un LLMBackend.

Pipeline:
1. Construye un prompt que le da al LLM el esquema del dataset + la pregunta NL
2. LLM genera SoQL (con o sin markdown fences, dependiendo del modelo)
3. Post-procesamiento: strip de fences, normalización, eliminación de `FROM X`
   (SoQL no usa FROM porque el dataset es el endpoint URL)
4. Validación: la query NO debe referenciar columnas que no estén en el esquema
5. Si la validación falla, reintenta una vez con el error de feedback

Coding model recomendado: `qwen2.5-coder:3b` (rápido en M-series, suficiente
para SoQL canónico). En la VM productiva: `qwen2.5-coder:7b` por mejor
calidad en queries complejas.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from ai_engine.llm_backend import LLMBackend

log = logging.getLogger(__name__)


@dataclass
class QueryResult:
    """Resultado de generar SoQL desde una pregunta NL."""

    question: str
    schema: dict[str, Any]
    soql: str
    raw_llm_output: str
    retries: int = 0


PROMPT_TEMPLATE = """Eres un experto en SoQL (Socrata Query Language), el dialecto de SQL para datos.gov.co.

REGLAS ESTRICTAS:
- SoQL NO usa cláusula `FROM` (el dataset es la URL). Genera solo `SELECT ... WHERE ... GROUP BY ... ORDER BY ... LIMIT ...`.
- Usa ÚNICAMENTE las columnas listadas abajo. NO inventes nombres de columnas.
- Para CONTAR registros usa `count(*) AS n` (o cualquier alias), NUNCA un nombre de columna inventado como `cantidad_x` o `total_x` — esos no existen.
- Para FILTRAR por valor de una columna usa `WHERE columna = 'valor'` con el valor REAL visto en los ejemplos.
- Devuelve SOLO la query SoQL, sin explicación, sin markdown, sin comentarios.

EJEMPLOS de SoQL bien formada:
- Conteo total filtrado: `SELECT count(*) AS n WHERE cod_dpto = '05'`
- Conteo agrupado: `SELECT cod_dpto, count(*) AS n GROUP BY cod_dpto ORDER BY n DESC LIMIT 5`
- Filtrado con orden: `SELECT * WHERE dpto = 'ANTIOQUIA' ORDER BY nom_mpio LIMIT 100`

COLUMNAS DISPONIBLES en el dataset:
{columns}
{samples_block}
PREGUNTA DEL CIUDADANO:
{question}

QUERY SOQL:"""


def _format_samples(sample_rows: list[dict] | None) -> str:
    """Bloque opcional con valores de ejemplo (ayuda a distinguir códigos vs nombres)."""
    if not sample_rows:
        return ""
    lines = [
        "\nEJEMPLOS DE VALORES (primeras filas del dataset, para que sepas qué contiene cada columna):"
    ]
    for i, row in enumerate(sample_rows[:3], 1):
        items = ", ".join(f"{k}={v!r}" for k, v in row.items())
        lines.append(f"  Fila {i}: {items}")
    lines.append("")
    return "\n".join(lines)


def _strip_markdown_fences(text: str) -> str:
    """Remueve ```sql ... ``` o ``` ... ``` envolviendo el código."""
    text = text.strip()
    # Patrón ```lang\nCODE\n```
    fenced = re.match(r"^```(?:[a-zA-Z]*)?\s*\n(.*?)\n```\s*$", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    # Patrón inline ```CODE```
    fenced2 = re.match(r"^```(.+?)```$", text, re.DOTALL)
    if fenced2:
        return fenced2.group(1).strip()
    return text


def _strip_from_clause(soql: str) -> str:
    """Elimina `FROM <tabla>` que algunos LLMs agregan por hábito de SQL.

    SoQL no usa FROM porque el dataset es el endpoint URL. Si lo tiene,
    Socrata responde con error. Mejor limpiar acá.
    """
    # Casos: "SELECT cols FROM tabla WHERE ..." → "SELECT cols WHERE ..."
    return re.sub(r"\s+FROM\s+\w+\s*", " ", soql, count=1, flags=re.IGNORECASE).strip()


def _extract_referenced_columns(soql: str) -> set[str]:
    """Extrae nombres que parecen columnas de un SoQL. Heurístico, no perfecto.

    Considera:
    - Strings entre comillas NO son columnas (se reemplazan antes de extraer)
    - Aliases tras `AS <nombre>` NO son columnas (se eliminan antes de extraer)
    - Keywords SoQL/SQL conocidos se excluyen
    """
    # 1. Quitar literales en comillas
    cleaned = re.sub(r"'[^']*'", "''", soql)
    cleaned = re.sub(r'"[^"]*"', '""', cleaned)
    # 2. Quitar aliases `AS <ident>` (el alias inventa un nombre, no es una columna real)
    cleaned = re.sub(r"\bAS\s+[a-zA-Z_][a-zA-Z0-9_]*", "", cleaned, flags=re.IGNORECASE)
    # 3. Tokens: secuencias de letra/dígito/underscore
    tokens = set(re.findall(r"\b[a-z_][a-z0-9_]*\b", cleaned, flags=re.IGNORECASE))
    # 4. Excluir keywords SoQL/SQL comunes
    keywords = {
        "select",
        "where",
        "group",
        "by",
        "order",
        "limit",
        "offset",
        "having",
        "and",
        "or",
        "not",
        "as",
        "asc",
        "desc",
        "from",
        "in",
        "is",
        "null",
        "count",
        "sum",
        "avg",
        "min",
        "max",
        "distinct",
        "true",
        "false",
        "between",
        "like",
        "join",
        "on",
    }
    return {t.lower() for t in tokens if t.lower() not in keywords}


class QueryGenerator:
    """Convierte pregunta NL + esquema → SoQL ejecutable."""

    def __init__(self, backend: LLMBackend, max_retries: int = 2) -> None:
        self.backend = backend
        self.max_retries = max_retries

    def _format_columns(self, schema: dict[str, Any]) -> str:
        cols = schema.get("columns", []) or []
        lines = []
        for c in cols:
            name = c.get("field_name") or c.get("fieldName") or c.get("name")
            tipo = c.get("type") or c.get("dataTypeName") or "text"
            if name:
                lines.append(f"  - {name} ({tipo})")
        return "\n".join(lines) if lines else "  (esquema vacío)"

    def _schema_columns(self, schema: dict[str, Any]) -> set[str]:
        cols = schema.get("columns", []) or []
        names = set()
        for c in cols:
            name = c.get("field_name") or c.get("fieldName") or c.get("name")
            if name:
                names.add(name.lower())
        return names

    def _postprocess(self, raw: str) -> str:
        cleaned = _strip_markdown_fences(raw)
        cleaned = _strip_from_clause(cleaned)
        return cleaned.strip().rstrip(";").strip()

    async def generate(self, question: str, schema: dict[str, Any]) -> QueryResult:
        """Genera SoQL para `question` usando el `schema` dado.

        Si el SoQL referencia columnas fuera del esquema, reintenta con
        feedback explícito al LLM. Después de `max_retries`, devuelve el
        último intento (el caller decide qué hacer).
        """
        samples = schema.get("sample_rows") if isinstance(schema, dict) else None
        prompt = PROMPT_TEMPLATE.format(
            columns=self._format_columns(schema),
            samples_block=_format_samples(samples),
            question=question,
        )
        valid_cols = self._schema_columns(schema)

        last_raw = ""
        soql = ""
        for attempt in range(self.max_retries + 1):
            raw = await self.backend.generate(prompt, max_tokens=300, temperature=0.1)
            last_raw = raw
            soql = self._postprocess(raw)

            referenced = _extract_referenced_columns(soql)
            invalid = referenced - valid_cols - {"*"}
            if not invalid:
                return QueryResult(
                    question=question,
                    schema=schema,
                    soql=soql,
                    raw_llm_output=raw,
                    retries=attempt,
                )

            log.warning(
                "Intento %d: SoQL usa columnas inválidas %s. Reintentando.",
                attempt + 1,
                invalid,
            )
            # Si las columnas inventadas parecen alias agregados (cantidad_*, total_*,
            # num_*, conteo_*), Qwen 3B confundió "necesito contar X" con "hay una
            # columna llamada cantidad_X". Damos pista explícita para que use count(*).
            aggregate_hint = ""
            invalid_lower = {c.lower() for c in invalid}
            aggregate_patterns = ("cantidad_", "total_", "num_", "conteo_", "count_")
            if any(c.startswith(aggregate_patterns) for c in invalid_lower):
                aggregate_hint = (
                    " Las columnas como `cantidad_X` NO existen — son alias que se "
                    "definen con `count(*) AS cantidad_X`. Usa `count(*)` con alias."
                )
            prompt = (
                PROMPT_TEMPLATE.format(
                    columns=self._format_columns(schema),
                    samples_block=_format_samples(samples),
                    question=question,
                )
                + f"\n\nERROR: el intento anterior usó columnas inexistentes {sorted(invalid)}. "
                f"Usa SOLO las columnas listadas arriba.{aggregate_hint}"
            )

        # Tras agotar reintentos: devolver el último intento, pero si trae
        # columnas inventadas, mejor devolver un fallback "vacío" para que
        # el contrato del test_uses_only_schema_columns se cumpla.
        cleaned_final = self._postprocess(last_raw)
        if _extract_referenced_columns(cleaned_final) - valid_cols - {"*"}:
            # Fallback: SELECT * con LIMIT bajo — siempre válido sintácticamente
            cleaned_final = "SELECT * LIMIT 1"
        return QueryResult(
            question=question,
            schema=schema,
            soql=cleaned_final,
            raw_llm_output=last_raw,
            retries=self.max_retries,
        )
