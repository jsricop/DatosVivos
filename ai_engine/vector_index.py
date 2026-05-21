"""Índice vectorial de metadatos de datasets (ChromaDB persistido).

Embebe `name + description + tags` de cada dataset del catálogo datos.gov.co
usando el modelo multilingüe `intfloat/multilingual-e5-base`. Permite búsqueda
semántica desde lenguaje natural a IDs de datasets relevantes.

Decisiones de diseño:
- ChromaDB sobre FAISS por persistencia simple en disco (ver ADR-005).
- e5-multilingual-base por su soporte explícito de español y tamaño moderado.
- e5 requiere prefijos `passage:` (al indexar) y `query:` (al buscar) — el
  cliente los aplica internamente, el caller pasa texto plano.
- Métrica: cosine distance. `score = 1 - distance` en [0, 1].
- Filtro de relevancia `min_score` (default 0.83): drop matches por debajo
  del umbral. Calibrado empíricamente sobre el catálogo completo:
    * Queries reales: top scores en [0.84, 0.89]
    * Queries nonsense: top scores en [0.77, 0.81]
  El threshold 0.83 separa ambos rangos sin falsos negativos sobre el set
  de queries de evaluación.
- Si nada supera el threshold, `search` retorna lista vacía — mejor para el
  LLM consumidor que devolver resultados ruidosos.
- Nota: margin-based filtering (top vs median) NO funciona con embeddings
  modernos tipo e5 porque queries legítimas con muchos matches relevantes
  (ej. "DIVIPOLA" → varios datasets DIVIPOLA) tienen margin similar a
  queries nonsense. Discriminar por score absoluto es más robusto.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)

DEFAULT_MODEL = "intfloat/multilingual-e5-base"
DEFAULT_COLLECTION = "datos_gov_co"
DEFAULT_INDEX_PATH = Path("./data/vector_index")
# Calibrado empíricamente sobre el catálogo completo de datos.gov.co (~8.000 datasets)
# con e5-multilingual-base: queries reales producen top scores en [0.84, 0.89], queries
# nonsense en [0.77, 0.81]. Threshold 0.83 separa ambos rangos sin falsos negativos.
DEFAULT_MIN_SCORE = 0.83


@dataclass(frozen=True)
class SearchResult:
    """Resultado de una búsqueda vectorial."""

    id: str
    name: str
    entity: str | None
    score: float
    description: str | None = None
    category: str | None = None


class VectorIndex:
    """Índice vectorial persistido sobre el catálogo de datos.gov.co."""

    def __init__(
        self,
        path: Path | str | None = None,
        model_name: str = DEFAULT_MODEL,
        collection_name: str = DEFAULT_COLLECTION,
        min_score: float = DEFAULT_MIN_SCORE,
    ) -> None:
        self.path = Path(path) if path else Path(os.getenv("INDEX_PATH", DEFAULT_INDEX_PATH))
        self.path.mkdir(parents=True, exist_ok=True)
        self.min_score = min_score
        self._model_name = model_name
        self._collection_name = collection_name
        self._model: SentenceTransformer | None = None
        self._client = chromadb.PersistentClient(
            path=str(self.path),
            settings=ChromaSettings(anonymized_telemetry=False, allow_reset=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def load(cls, path: Path | str | None = None) -> VectorIndex:
        """Carga el índice persistido (crea uno vacío si no existe)."""
        return cls(path=path)

    @property
    def model(self) -> SentenceTransformer:
        """Lazy-load del modelo de embeddings (~280 MB, primera vez descarga)."""
        if self._model is None:
            log.info("Cargando modelo de embeddings: %s", self._model_name)
            self._model = SentenceTransformer(self._model_name)
        return self._model

    def __len__(self) -> int:
        return self._collection.count()

    def existing_ids(self, candidate_ids: list[str]) -> set[str]:
        """Devuelve cuáles de los `candidate_ids` ya están indexados.

        Útil para implementar idempotencia en build_index: el caller filtra
        los IDs nuevos antes de generar embeddings (costoso) y hacer upsert
        (que en ChromaDB reconstruye HNSW e infla disco aún con la misma data).
        """
        if not candidate_ids:
            return set()
        result = self._collection.get(ids=[str(i) for i in candidate_ids], include=[])
        return set(result.get("ids") or [])

    def _build_document_text(
        self,
        name: str,
        description: str | None,
        tags: list[str] | None,
        entity: str | None,
        category: str | None,
    ) -> str:
        """Texto que se embebe — combina campos relevantes para matching semántico."""
        parts = [name]
        if entity:
            parts.append(f"Entidad: {entity}")
        if category:
            parts.append(f"Categoría: {category}")
        if description:
            parts.append(description)
        if tags:
            parts.append("Etiquetas: " + ", ".join(tags))
        return " | ".join(parts)

    def upsert_many(self, datasets: list[dict[str, Any]]) -> int:
        """Inserta o actualiza N datasets en el índice. Idempotente por `id`.

        Args:
            datasets: lista de dicts con al menos {id, name}; opcionalmente
                description, tags, entity, category.

        Returns:
            Número de datasets procesados.
        """
        if not datasets:
            return 0

        ids = [str(d["id"]) for d in datasets]
        documents = [
            self._build_document_text(
                name=d.get("name") or "",
                description=d.get("description"),
                tags=d.get("tags"),
                entity=d.get("entity"),
                category=d.get("category"),
            )
            for d in datasets
        ]
        # e5: prefijo "passage:" para documentos indexados
        passages = [f"passage: {doc}" for doc in documents]
        embeddings = self.model.encode(
            passages,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()
        metadatas = [
            {
                "name": d.get("name") or "",
                "entity": d.get("entity") or "",
                "description": (d.get("description") or "")[:500],  # cap para metadata
                "category": d.get("category") or "",
                "tags": ", ".join(d.get("tags") or []),
            }
            for d in datasets
        ]
        self._collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
        return len(datasets)

    def search(self, query: str, k: int = 5) -> list[SearchResult]:
        """Busca los k datasets más relevantes para la query en lenguaje natural.

        Filtra resultados con score < `self.min_score`. Si nada supera el threshold,
        retorna lista vacía — preferible a devolver ruido al LLM consumidor.

        Args:
            query: pregunta o keywords en español (o cualquier idioma soportado por e5).
            k: número máximo de resultados a retornar.

        Returns:
            Lista de `SearchResult` ordenados por score descendente.
        """
        if not query or not query.strip():
            return []
        if self.__len__() == 0:
            log.warning("VectorIndex vacío — corre scripts/build_index.py primero.")
            return []

        # e5: prefijo "query:" para queries
        q_emb = self.model.encode(
            [f"query: {query.strip()}"],
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        ).tolist()

        raw = self._collection.query(
            query_embeddings=q_emb,
            n_results=k,
        )
        ids = raw.get("ids", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        if not ids:
            return []

        scores = [1.0 - float(d) for d in distances]

        results: list[SearchResult] = []
        for i, score, meta in zip(ids, scores, metadatas, strict=False):
            if score < self.min_score:
                continue
            results.append(
                SearchResult(
                    id=i,
                    name=meta.get("name") or "",
                    entity=meta.get("entity") or None,
                    score=score,
                    description=meta.get("description") or None,
                    category=meta.get("category") or None,
                )
            )
        return results

    def get_by_id(self, dataset_id: str) -> SearchResult | None:
        """Recupera un dataset específico por ID, sin pasar por similitud.

        Útil para inyectar datasets autoritativos en el retrieval cuando
        un patrón de pregunta lo amerita (ej. DIVIPOLA para preguntas de
        conteo de mpios/dptos). Score default = 0.9 (alto, para que el
        boost lo prioritice si aplica).
        """
        if not dataset_id:
            return None
        try:
            raw = self._collection.get(ids=[dataset_id])
        except Exception as exc:  # noqa: BLE001
            log.warning("get_by_id falló (%s): %s", dataset_id, exc)
            return None
        ids = raw.get("ids", [])
        metadatas = raw.get("metadatas", [])
        if not ids or not metadatas:
            return None
        meta = metadatas[0] or {}
        return SearchResult(
            id=ids[0],
            name=meta.get("name") or "",
            entity=meta.get("entity") or None,
            score=0.9,
            description=meta.get("description") or None,
            category=meta.get("category") or None,
        )

    def reset(self) -> None:
        """Borra toda la colección. Útil para tests, NO usar en producción."""
        self._client.delete_collection(self._collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self._collection_name,
            metadata={"hnsw:space": "cosine"},
        )
