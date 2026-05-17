# ADR-005: ChromaDB en vez de pgvector

**Estado:** Aceptada
**Fecha:** Sprint 2

## Decisión

Almacenar el índice vectorial de los 8 389 datasets en **ChromaDB** (persistencia local en disco), no en **pgvector** (extensión de PostgreSQL).

## Razón

- **Más simple de implementar.** ChromaDB se construye con `chromadb.PersistentClient(path=...)`; sin servicio adicional.
- **Independiente de PostgreSQL.** El motor de IA no se cae si Postgres no está activo.
- **Persistencia en disco** sin gestionar tablas SQL ni migraciones.
- **Búsqueda por similitud coseno** out of the box.

## Trade-off

- **Otra dependencia.** ChromaDB suma una librería al stack.
- **Sin queries SQL sobre los vectores.** Si en el futuro quisiéramos joins entre embeddings y otras tablas, pgvector sería natural; con ChromaDB hay que orquestar fuera.
- **Migración evaluable.** Si se decide activar PostgreSQL para logging (ver [ADR-004](./004-postgresql-vs-sqlite.md)), reconsiderar mover el índice a pgvector para consolidar.

## Referencias

- `ai_engine/vector_index.py`
- `scripts/build_index.py`
- [`docs/crisp_mlq/03_data_preparation.md`](../crisp_mlq/03_data_preparation.md)
