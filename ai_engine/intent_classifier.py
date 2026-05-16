"""Clasificador de intención por similitud coseno sobre embeddings multilingual-e5.

Categoriza una pregunta en lenguaje natural en una de 5 intenciones:

- `search`        — pregunta por la EXISTENCIA o disponibilidad de datos
- `descriptive`   — pide describir contenido específico (listar, mostrar, etc.)
- `comparative`   — implica comparación entre entidades o categorías
- `temporal`      — implica análisis sobre el tiempo (evolución, tendencia)
- `cross_source`  — explícitamente pide combinar/cruzar múltiples fuentes

Técnica:
1. Pre-computar centroide (media de embeddings) de un set de prototipos por categoría.
2. Para clasificar: embebber la pregunta, calcular cosine sim a cada centroide,
   devolver argmax.

Los prototipos están deliberadamente DESACOPLADOS del held-out set de tests
(`tests/test_sprint2_acceptance.py::INTENT_TEST_SET`) para que la métrica de
accuracy mida generalización, no memorización.

Latencia esperada: < 100 ms por clasificación en CPU (1 embedding + 5 dot
products contra vectores de 768 dim).
"""

from __future__ import annotations

import logging
from typing import Final

import numpy as np
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

DEFAULT_MODEL = "intfloat/multilingual-e5-base"

# 5 categorías oficiales (documentado en MAIN.md §10.3 y docs/architecture.md).
CATEGORIES: Final[tuple[str, ...]] = (
    "search",
    "descriptive",
    "comparative",
    "temporal",
    "cross_source",
)


# Prototipos: 8 ejemplos por categoría. Diseñados para CAPTURAR el patrón
# semántico sin solapar con INTENT_TEST_SET (held-out).
PROTOTYPES: Final[dict[str, list[str]]] = {
    "search": [
        "qué datasets están publicados sobre vivienda",
        "información disponible sobre comercio exterior",
        "el catálogo tiene algo sobre minería",
        "existe data acerca de migración",
        "consigue datos relacionados con turismo rural",
        "qué se ha publicado sobre agricultura",
        "hay registros sobre cultura ciudadana",
        "tienen datos disponibles sobre ambiente",
    ],
    "descriptive": [
        "describe el contenido del dataset de hospitales",
        "enumera los productos de exportación",
        "cuál es el detalle de las columnas",
        "qué hay en este registro de víctimas",
        "explica las categorías incluidas",
        "qué información contiene el archivo de defensa",
        "muestra qué campos están disponibles",
        "dime el detalle de cada registro",
    ],
    "comparative": [
        "contrasta el desempeño de Bogotá frente a Cali",
        "qué región está por encima en cobertura",
        "diferencia de ingresos entre los departamentos",
        "ordena los municipios por inversión social",
        "Antioquia versus Valle en producción",
        "el departamento con mejor desempeño en salud",
        "cuál entidad gestiona más recursos comparada con las otras",
        "establece un ranking de ciudades por calidad de vida",
    ],
    "temporal": [
        "histórico del comercio exterior colombiano",
        "evolución del salario mínimo a lo largo del tiempo",
        "serie temporal de homicidios en los últimos años",
        "cambio del nivel educativo desde 1990",
        "trend de matrículas año a año",
        "comportamiento mes a mes del turismo nacional",
        "progresión anual del gasto público",
        "X a través de las décadas",
    ],
    "cross_source": [
        "vinculando salud con educación por municipio",
        "agrupa información del Mineducación con el ICFES",
        "asociación entre inversión y resultados PISA",
        "joinea los datos de empleo con los de pobreza",
        "merge entre presupuesto y ejecución por entidad",
        "intersección de datos del DNP y el DANE",
        "relaciona el dataset de salud con el de población",
        "combina los registros del MEN y los del SISBÉN",
    ],
}


class IntentClassifier:
    """Clasificador por similitud a centroides de prototipos."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model_name = model_name
        self._model: SentenceTransformer | None = None
        self._centroids: dict[str, np.ndarray] = {}
        # Forzar carga del modelo y cómputo de centroides en init para que la
        # primera llamada a classify() ya esté warm.
        self._init_centroids()

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            log.info("Cargando modelo de embeddings: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def _encode_query(self, texts: list[str]) -> np.ndarray:
        """Embebe textos con prefijo `query:` exigido por e5."""
        prefixed = [f"query: {t}" for t in texts]
        return self.model.encode(
            prefixed,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )

    def _init_centroids(self) -> None:
        log.info("Calculando centroides de %d categorías...", len(PROTOTYPES))
        for category, examples in PROTOTYPES.items():
            embeddings = self._encode_query(examples)
            centroid = embeddings.mean(axis=0)
            # Re-normalizar la media (suma de unit vectors NO es unit)
            centroid /= np.linalg.norm(centroid)
            self._centroids[category] = centroid
        log.info("Centroides listos.")

    def classify(self, text: str) -> str:
        """Devuelve la categoría más cercana al embedding de `text`."""
        if not text or not text.strip():
            return "search"  # fallback razonable para queries vacíos

        q_emb = self._encode_query([text.strip()])[0]
        best_cat = "search"
        best_score = -1.0
        for category, centroid in self._centroids.items():
            score = float(np.dot(q_emb, centroid))
            if score > best_score:
                best_score = score
                best_cat = category
        return best_cat

    def classify_with_score(self, text: str) -> tuple[str, float]:
        """Como `classify` pero también devuelve la similitud al centroide ganador."""
        if not text or not text.strip():
            return ("search", 0.0)
        q_emb = self._encode_query([text.strip()])[0]
        best_cat = "search"
        best_score = -1.0
        for category, centroid in self._centroids.items():
            score = float(np.dot(q_emb, centroid))
            if score > best_score:
                best_score = score
                best_cat = category
        return (best_cat, best_score)
