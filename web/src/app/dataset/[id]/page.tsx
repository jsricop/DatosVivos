import Link from "next/link";
import { notFound } from "next/navigation";

import { Icon } from "@/components/Icon";
import { fetchDatasetMetadata } from "@/lib/api";

type Params = { id: string };

export default async function DatasetPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const data = await fetchDatasetMetadata(id);
  if (!data) notFound();

  return (
    <div
      className="container-narrow"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-6)",
        paddingBlock: "var(--space-7)",
      }}
    >
      <Link
        href="/"
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--type-caption)",
          color: "var(--ink-2)",
        }}
      >
        ← volver
      </Link>

      <header
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 8,
          paddingBlockEnd: "var(--space-4)",
          borderBlockEnd: "1px solid var(--hairline)",
        }}
      >
        <span className="kicker">
          {data.entity ?? "Entidad no declarada"}
        </span>
        <h1
          style={{
            margin: 0,
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h1)",
          }}
        >
          {data.name}
        </h1>
        {data.description ? (
          <p
            className="measure"
            style={{
              margin: "12px 0 0 0",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-lg)",
              color: "var(--ink-2)",
              lineHeight: 1.6,
            }}
          >
            {data.description}
          </p>
        ) : null}
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(260px, 1fr) 2fr",
          gap: "var(--space-6)",
        }}
      >
        <section aria-label="Metadata">
          <span className="kicker" style={{ display: "block", marginBlockEnd: 12 }}>
            Ficha técnica
          </span>
          <dl
            style={{
              margin: 0,
              display: "grid",
              gridTemplateColumns: "auto 1fr",
              rowGap: 10,
              columnGap: 16,
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-2)",
            }}
          >
            <dt>ID</dt>
            <dd style={{ margin: 0, color: "var(--ink)" }}>{data.id}</dd>
            {data.last_updated ? (
              <>
                <dt>Actualizado</dt>
                <dd style={{ margin: 0, color: "var(--ink)" }}>{data.last_updated}</dd>
              </>
            ) : null}
            {typeof data.row_count === "number" ? (
              <>
                <dt>Filas</dt>
                <dd style={{ margin: 0, color: "var(--ink)", fontVariantNumeric: "tabular-nums" }}>
                  {data.row_count.toLocaleString("es-CO")}
                </dd>
              </>
            ) : null}
            <dt>Columnas</dt>
            <dd style={{ margin: 0, color: "var(--ink)" }}>{data.columns.length}</dd>
            <dt>Página</dt>
            <dd style={{ margin: 0 }}>
              <a href={data.url} target="_blank" rel="noopener noreferrer">
                datos.gov.co
                <Icon name="external-link" size={12} aria-hidden style={{ marginInlineStart: 4, verticalAlign: "baseline" }} />
              </a>
            </dd>
            <dt>API</dt>
            <dd style={{ margin: 0 }}>
              <a href={data.api_url} target="_blank" rel="noopener noreferrer">
                JSON SODA
                <Icon name="external-link" size={12} aria-hidden style={{ marginInlineStart: 4, verticalAlign: "baseline" }} />
              </a>
            </dd>
          </dl>
        </section>

        <section aria-label="Columnas">
          <span className="kicker" style={{ display: "block", marginBlockEnd: 12 }}>
            Esquema de columnas
          </span>
          {data.columns.length === 0 ? (
            <p
              style={{
                fontFamily: "var(--font-sans)",
                fontSize: "var(--type-body-sm)",
                color: "var(--ink-muted)",
              }}
            >
              Sin metadata de columnas disponible.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th scope="col">Campo</th>
                  <th scope="col">Tipo</th>
                  <th scope="col">Descripción</th>
                </tr>
              </thead>
              <tbody>
                {data.columns.map((col) => (
                  <tr key={col.field_name}>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--ink)" }}>
                      {col.field_name}
                    </td>
                    <td style={{ fontFamily: "var(--font-mono)", color: "var(--ink-2)" }}>
                      {col.data_type}
                    </td>
                    <td style={{ fontFamily: "var(--font-sans)" }}>
                      {col.description ?? "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
    </div>
  );
}
