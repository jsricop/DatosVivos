# Glosario — DatosVivos

Términos del dominio que aparecen en el código, la documentación y las conversaciones del proyecto. Útil para nuevos contribuidores y agentes de IA sin contexto previo.

## Datos públicos colombianos

### datos.gov.co
Portal de datos abiertos del Estado colombiano. Operado por MinTIC. Contiene ~8.000 datasets publicados por entidades nacionales y territoriales. Corre sobre la plataforma **Socrata**.

### DIVIPOLA
División Político-Administrativa de Colombia. Sistema oficial de códigos del DANE para identificar departamentos (2 dígitos), municipios (5 dígitos), centros poblados, etc. Es la **clave canónica** para cruzar datasets de territorios.

Ejemplos: `05` = Antioquia, `05001` = Medellín, `25` = Cundinamarca.

Dataset de referencia: `gdxc-w37w` (DIVIPOLA-Códigos municipios).

### DANE
Departamento Administrativo Nacional de Estadística. Productor oficial de DIVIPOLA y de muchos datasets estadísticos clave.

### NIT
Número de Identificación Tributaria. Usado como clave para cruzar datasets sobre empresas/personas jurídicas.

### Entidad publicadora
La organización del Estado que publica un dataset en datos.gov.co. Aparece en el campo `attribution` de la metadata. Ejemplos: MinSalud, DNP, Gobernación de Antioquia, etc.

## Stack técnico

### Socrata
Plataforma cloud (hoy parte de Tyler Technologies) que muchos gobiernos del mundo usan para publicar datos abiertos. datos.gov.co es un cliente de Socrata, igual que NYC Open Data, Chicago Data Portal, data.gov (USA), etc.

### SODA API
Socrata Open Data API. Endpoint para **consultar datos** de un dataset. URL: `https://www.datos.gov.co/resource/{dataset_id}.json`. Acepta queries SoQL.

### Discovery API
API federada de Socrata para **buscar datasets** en todo el ecosistema. Endpoint: `https://api.us.socrata.com/api/catalog/v1`. Se puede filtrar por dominio (`domains=www.datos.gov.co`).

### Metadata API
API para obtener el **esquema** de un dataset (columnas, tipos, descripción). URL: `https://www.datos.gov.co/api/views/{dataset_id}.json`.

### SoQL
Socrata Query Language. Sintaxis similar a SQL para consultar datasets vía SODA API. Soporta `$select`, `$where`, `$group`, `$order`, `$limit`, `$offset`. Ejemplo:

```sql
SELECT dpto, count(*) AS n GROUP BY dpto ORDER BY n DESC LIMIT 5
```

### MCP (Model Context Protocol)
Protocolo abierto publicado por Anthropic en nov/2024 para estandarizar cómo los LLMs consumen tools externas. Define un formato JSON-RPC y transportes (stdio, SSE) para que un cliente (host del LLM) hable con un server (que expone las tools). Spec: <https://modelcontextprotocol.io>.

### FastMCP
Framework Python del SDK oficial de MCP para construir servers con decoradores. Lo usamos en `mcp_server/server.py`.

### Tool (MCP)
Función expuesta por un MCP Server al LLM. Tiene nombre, descripción en lenguaje natural, y un JSON Schema de input. El LLM lee este catálogo y decide cuándo y cómo llamarla.

### RAG
Retrieval-Augmented Generation. Patrón donde antes de generar respuesta, el LLM consulta un índice (típicamente vectorial) para traer contexto relevante. En DatosVivos lo usamos sobre los metadatos del catálogo (Sprint 2).

## Modelos y técnicas

### Ollama
Servidor local de modelos LLM que permite correr modelos cuantizados (GGUF) en CPU/GPU sin enviar datos a APIs externas. Lo usamos en Sprint 3 para servir Qwen y Llama.

### Qwen 2.5 Coder 7B (Q4_K_M)
Modelo LLM de Alibaba, especializado en código y consultas estructuradas. 7B parámetros, cuantización Q4_K_M (~5 GB RAM). Modelo primario de DatosVivos para generar SoQL.

### Llama 3 8B (Q4_K_M)
Modelo LLM de Meta. Fallback de Qwen. Mejor en narrativa en español.

### sentence-transformers / multilingual-e5-base
Modelo de embeddings multilingüe (Microsoft) que mapea texto a vectores de 768 dimensiones. Lo usamos para el clasificador de intención y el índice vectorial.

### ChromaDB
Base de datos vectorial open-source. Persistencia en disco. Búsqueda por similitud coseno. Alternativa considerada: FAISS (ver ADR-005).

## Conceptos CRISP-ML(Q)

### CRISP-ML(Q)
Cross-Industry Standard Process for Machine Learning with Quality assurance. Metodología en 6 fases (Business Understanding, Data Understanding, Data Preparation, Modeling, Evaluation, Deployment & Monitoring). Requerida por el concurso.

### Precision@k
Métrica de búsqueda: fracción de resultados relevantes en los primeros k retornados. La usamos para evaluar el índice vectorial.

### Intent classification
Clasificación de la intención de una pregunta NL en un conjunto fijo de categorías. En DatosVivos: `search`, `descriptive`, `comparative`, `temporal`, `cross_source`.

## Concurso / contexto

### Datos al Ecosistema 2026
Concurso de MinTIC para impulsar el uso de datos abiertos con IA. Cierre: 13 julio 2026. Sustentación: 14-17 julio. Finalistas: 24 julio. Final presencial: 1ra semana agosto.

### Reto #07
"Innovación y Tecnología: Diseñar asistentes virtuales que faciliten el acceso ciudadano a datos abiertos". Es el reto en el que participa DatosVivos.

### ANI
Agencia Nacional de Infraestructura. Entidad para la cual trabaja el equipo. La Oficina de Tecnología lidera DatosVivos.
