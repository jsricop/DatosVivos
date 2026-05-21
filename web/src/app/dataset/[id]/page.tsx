import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { Icon } from "@/components/Icon";
import { fetchDatasetMetadata } from "@/lib/api";

type Params = { id: string };

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { id } = await params;
  const data = await fetchDatasetMetadata(id);
  if (!data) {
    return {
      title: `Dataset ${id}`,
      robots: { index: false, follow: true },
    };
  }
  const entity = data.entity ? ` · ${data.entity}` : "";
  const short =
    data.description?.length > 160
      ? `${data.description.slice(0, 157)}…`
      : (data.description ?? "");
  return {
    title: `${data.name}${entity}`,
    description:
      short ||
      `Ficha técnica del dataset ${data.name} en datos.gov.co — esquema, columnas y enlaces verificables.`,
    alternates: { canonical: `/dataset/${id}` },
    openGraph: {
      type: "article",
      url: `/dataset/${id}`,
      title: `${data.name}${entity}`,
      description: short || `Ficha técnica de ${data.name} sobre datos.gov.co.`,
    },
    other: {
      "datasetvivos:dataset-id": id,
      ...(data.entity ? { "datasetvivos:entity": data.entity } : {}),
    },
  };
}

export default async function DatasetPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { id } = await params;
  const data = await fetchDatasetMetadata(id);
  if (!data) notFound();

  // JSON-LD schema.org/Dataset — habilita rich snippets en Google Dataset
  // Search y describe la fuente verificable para crawlers institucionales.
  const datasetLd = {
    "@context": "https://schema.org",
    "@type": "Dataset",
    name: data.name,
    description: data.description || data.name,
    identifier: data.id,
    url: data.url,
    keywords: [data.entity, "datos abiertos", "Colombia"].filter(Boolean),
    inLanguage: "es-CO",
    isAccessibleForFree: true,
    license: "https://www.datos.gov.co/about",
    creator: data.entity
      ? { "@type": "Organization", name: data.entity }
      : undefined,
    distribution: [
      {
        "@type": "DataDownload",
        encodingFormat: "application/json",
        contentUrl: data.api_url,
      },
    ],
  };

  return (
    <div className="container-narrow flex flex-col gap-8 py-12">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(datasetLd) }}
      />
      <Link href="/" className="font-mono text-caption text-ink-2 focus-ring">
        ← volver
      </Link>

      <header className="flex flex-col gap-2 pb-4 hairline-bottom">
        <span className="text-kicker">
          {data.entity ?? "Entidad no declarada"}
        </span>
        <h1 className="m-0 font-serif text-h1">{data.name}</h1>
        {data.description ? (
          <p className="measure m-0 mt-3 font-sans text-body-lg text-ink-2 leading-relaxed">
            {data.description}
          </p>
        ) : null}
      </header>

      <div className="grid grid-cols-[minmax(260px,1fr)_2fr] gap-8">
        <section aria-label="Metadata">
          <span className="text-kicker block mb-3">Ficha técnica</span>
          <dl className="m-0 grid grid-cols-[auto_1fr] gap-y-2.5 gap-x-4 font-mono text-caption text-ink-2">
            <dt>ID</dt>
            <dd className="m-0 text-ink">{data.id}</dd>
            {data.last_updated ? (
              <>
                <dt>Actualizado</dt>
                <dd className="m-0 text-ink">{data.last_updated}</dd>
              </>
            ) : null}
            {typeof data.row_count === "number" ? (
              <>
                <dt>Filas</dt>
                <dd className="m-0 text-ink [font-variant-numeric:tabular-nums]">
                  {data.row_count.toLocaleString("es-CO")}
                </dd>
              </>
            ) : null}
            <dt>Columnas</dt>
            <dd className="m-0 text-ink">{data.columns.length}</dd>
            <dt>Página</dt>
            <dd className="m-0">
              <a
                href={data.url}
                target="_blank"
                rel="noopener noreferrer"
                className="focus-ring"
              >
                datos.gov.co
                <Icon
                  name="external-link"
                  size={12}
                  aria-hidden
                  style={{ marginInlineStart: 4, verticalAlign: "baseline" }}
                />
              </a>
            </dd>
            <dt>API</dt>
            <dd className="m-0">
              <a
                href={data.api_url}
                target="_blank"
                rel="noopener noreferrer"
                className="focus-ring"
              >
                JSON SODA
                <Icon
                  name="external-link"
                  size={12}
                  aria-hidden
                  style={{ marginInlineStart: 4, verticalAlign: "baseline" }}
                />
              </a>
            </dd>
          </dl>
        </section>

        <section aria-label="Columnas">
          <span className="text-kicker block mb-3">Esquema de columnas</span>
          {data.columns.length === 0 ? (
            <p className="font-sans text-body-sm text-ink-muted">
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
                    <td className="font-mono text-ink">{col.field_name}</td>
                    <td className="font-mono text-ink-2">{col.data_type}</td>
                    <td className="font-sans">{col.description ?? "—"}</td>
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
