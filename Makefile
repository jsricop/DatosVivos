# DatosVivos — atajos de operación local
#
# Objetivo: no recordar comandos largos. Documentar lo común.
# Asume que docker-compose está corriendo y SSH está disponible.
#
# Uso: make <target>

API := datosvivos-api-1
PG  := datosvivos-postgres-1
SSH := datosvivos


# ----------------------------------------------------------------------
# Eval / tests
# ----------------------------------------------------------------------

.PHONY: eval
eval:  ## Corre el golden set de chips contra producción
	@ssh $(SSH) 'docker exec $(API) python /app/eval/run_eval_chips.py --base-url https://datosvivos.co'

.PHONY: test
test:  ## Corre los unit tests dentro del contenedor api
	@ssh $(SSH) 'docker exec $(API) python -m pytest /app/tests/ -v 2>&1 | tail -40 || \
		docker exec $(API) python -c "import sys; sys.path.insert(0,\"/app\"); \
		from tests import test_soql_templates, test_validate_numbers, test_csv_cache, \
		test_duckdb_templates, test_nl_to_chips_guardrail; \
		import inspect; \
		for m in [test_soql_templates, test_validate_numbers, test_csv_cache, \
		test_duckdb_templates, test_nl_to_chips_guardrail]: \
		  ok=bad=0; \
		  [(\"\", inspect.getmembers(m, lambda f: inspect.isfunction(f) and f.__name__.startswith(\"test_\")))]; \
		  print(m.__name__)"'


# ----------------------------------------------------------------------
# Telemetría / observabilidad
# ----------------------------------------------------------------------

.PHONY: telemetry
telemetry:  ## Stats de adopción de chips path últimas 24h
	@ssh $(SSH) 'docker exec $(PG) psql -U dv -d datosvivos -c \
		"SELECT endpoint, COUNT(*) AS calls, \
		         AVG(elapsed_ms)::int AS avg_ms, \
		         MAX(elapsed_ms) AS max_ms, \
		         COUNT(*) FILTER (WHERE error IS NOT NULL) AS errors \
		 FROM chips_telemetry \
		 WHERE ts > NOW() - INTERVAL '\''1 day'\'' \
		 GROUP BY 1 ORDER BY calls DESC;"'

.PHONY: telemetry-hallucinations
telemetry-hallucinations:  ## Narrativas censuradas por el validator
	@ssh $(SSH) 'docker exec $(PG) psql -U dv -d datosvivos -c \
		"SELECT dataset_id, tipo, hallucinated, ts \
		 FROM chips_telemetry \
		 WHERE endpoint = '\''explain'\'' AND hallucinated > 0 \
		 ORDER BY ts DESC LIMIT 20;"'

.PHONY: telemetry-errors
telemetry-errors:  ## Endpoints con error en últimas 24h
	@ssh $(SSH) 'docker exec $(PG) psql -U dv -d datosvivos -c \
		"SELECT endpoint, error, COUNT(*) \
		 FROM chips_telemetry \
		 WHERE ts > NOW() - INTERVAL '\''1 day'\'' AND error IS NOT NULL \
		 GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 20;"'


# ----------------------------------------------------------------------
# Catálogo
# ----------------------------------------------------------------------

.PHONY: catalog-stats
catalog-stats:  ## Distribución del catálogo por source_portal
	@ssh $(SSH) 'docker exec $(PG) psql -U dv -d datosvivos -c \
		"SELECT source_portal, \
		         COUNT(*) AS datasets, \
		         COUNT(*) FILTER (WHERE federated_status = '\''ok'\'' OR source_type = '\''socrata'\'') AS consultables, \
		         COUNT(*) FILTER (WHERE entity_id IS NOT NULL) AS con_entity \
		 FROM datasets GROUP BY 1 ORDER BY datasets DESC;"'

.PHONY: catalog-entities
catalog-entities:  ## Top 15 entidades por # de datasets resueltos
	@ssh $(SSH) 'docker exec $(PG) psql -U dv -d datosvivos -c \
		"SELECT e.name, COUNT(*) AS n \
		 FROM datasets d JOIN entities e USING (entity_id) \
		 GROUP BY 1 ORDER BY n DESC LIMIT 15;"'


# ----------------------------------------------------------------------
# Cache CSV federado
# ----------------------------------------------------------------------

.PHONY: cache-status
cache-status:  ## Tamaño y # de archivos en cache CSV federado
	@ssh $(SSH) "docker exec $(API) du -sh /app/data/csv_cache 2>/dev/null; \
		docker exec $(API) sh -c 'echo Files: \$$(find /app/data/csv_cache -type f 2>/dev/null | wc -l)'"

.PHONY: cache-clear
cache-clear:  ## Borra TODO el cache CSV (forzará re-descargas)
	@ssh $(SSH) 'docker exec $(API) find /app/data/csv_cache -type f -delete && \
		echo "Cache limpiado"'


# ----------------------------------------------------------------------
# Operación
# ----------------------------------------------------------------------

.PHONY: etl-incremental
etl-incremental:  ## Corre el ETL incremental (lo que hará el cron)
	@ssh $(SSH) 'docker exec $(API) python -m scripts.etl_refresh_catalog --incremental'

.PHONY: harvest-bogota
harvest-bogota:
	@ssh $(SSH) 'docker exec $(API) python -m scripts.harvest_ckan --portal bogota'

.PHONY: harvest-cali
harvest-cali:
	@ssh $(SSH) 'docker exec $(API) python -m scripts.harvest_ckan --portal cali'

.PHONY: harvest-valle
harvest-valle:
	@ssh $(SSH) 'docker exec $(API) python -m scripts.harvest_ckan --portal valle'


# ----------------------------------------------------------------------
# Migraciones (solo aplicar la última)
# ----------------------------------------------------------------------

.PHONY: migrations
migrations:  ## Aplica todas las migraciones nuevas (cuidado: idempotentes pero las corre todas)
	@for m in db/migrations/*.sql; do \
		echo "=== $$m ==="; \
		ssh $(SSH) "cat $$m | docker exec -i $(PG) psql -U dv -d datosvivos 2>&1 | tail -3" || true; \
	done


# ----------------------------------------------------------------------
# Help
# ----------------------------------------------------------------------

.PHONY: help
help:  ## Muestra esta ayuda
	@grep -E '^[a-zA-Z_-]+:.*?##' Makefile | sort | awk 'BEGIN {FS = ":.*?##"}; {printf "  \033[36m%-25s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help
