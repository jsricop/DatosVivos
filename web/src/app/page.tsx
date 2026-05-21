import Link from "next/link";

import { HomeSearchPanel } from "@/components/HomeSearchPanel";
import { Wordmark } from "@/components/Wordmark";
import {
  fetchPopular,
  fetchSuggest,
} from "@/lib/api";
import type { Axis } from "@/components/ChipGroup";

export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function HomePage() {
  const [tema, tipo, territorio, entidad, popular] = await Promise.all([
    fetchSuggest("tema"),
    fetchSuggest("tipo"),
    fetchSuggest("territorio"),
    fetchSuggest("entidad"),
    fetchPopular(7),
  ]);

  const chips: Record<Axis, typeof tema> = { tema, tipo, territorio, entidad };

  return (
    <div
      className="container-narrow"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-7)",
        paddingBlock: "var(--space-7)",
      }}
    >
      <section
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "var(--space-5)",
        }}
      >
        <Wordmark asHeading size="display" />
        <p
          style={{
            margin: 0,
            maxInlineSize: "32ch",
            fontFamily: "var(--font-serif)",
            fontStyle: "italic",
            fontSize: "var(--type-h2)",
            fontWeight: 400,
            lineHeight: 1.25,
            color: "var(--ink-2)",
          }}
        >
          Datos del Estado, en tus palabras.
        </p>
        <p
          style={{
            margin: 0,
            maxInlineSize: "60ch",
            fontFamily: "var(--font-sans)",
            fontSize: "var(--type-body-lg)",
            color: "var(--ink-2)",
            lineHeight: 1.55,
          }}
        >
          Agente de IA con modelo local sobre{" "}
          <a href="https://www.datos.gov.co" target="_blank" rel="noopener noreferrer">
            datos.gov.co
          </a>
          . Cada cifra que ves está calculada con <code className="mono">pandas</code> sobre los
          datos reales del dataset citado. Cero cifras inventadas, trazabilidad por enlace.
        </p>
      </section>

      <HomeSearchPanel chips={chips} />

      <section className="hairline-top" style={{ paddingBlockStart: "var(--space-6)" }}>
        <h2
          className="kicker"
          style={{ fontFamily: undefined, marginBlockEnd: 16 }}
        >
          Lo más consultado esta semana
        </h2>
        {popular.length > 0 ? (
          <ol
            style={{
              counterReset: "popular",
              listStyle: "none",
              display: "grid",
              gap: 12,
            }}
          >
            {popular.map((p, i) => (
              <li
                key={`${p.question}-${i}`}
                style={{
                  display: "grid",
                  gridTemplateColumns: "auto 1fr auto",
                  gap: 16,
                  alignItems: "baseline",
                  paddingBlock: 8,
                  borderBlockEnd: "1px solid var(--hairline)",
                }}
              >
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontVariantNumeric: "tabular-nums",
                    fontSize: "var(--type-body)",
                    color: "var(--accent)",
                    fontWeight: 500,
                  }}
                >
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Link
                  href={`/buscar?q=${encodeURIComponent(p.question)}`}
                  style={{
                    fontFamily: "var(--font-serif)",
                    fontSize: "var(--type-body-lg)",
                    color: "var(--ink)",
                  }}
                >
                  {p.question}
                </Link>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--type-kicker)",
                    color: "var(--ink-muted)",
                    fontVariantNumeric: "tabular-nums",
                  }}
                >
                  {p.count} consultas
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-muted)",
              maxInlineSize: "60ch",
            }}
          >
            Aún no hay consultas suficientes para componer este ranking. Empieza
            haciendo tu primera pregunta — la telemetría es anónima y se queda
            en la máquina del Estado.
          </p>
        )}
      </section>

      <section
        className="hairline-top"
        style={{
          paddingBlockStart: "var(--space-6)",
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "var(--space-5)",
        }}
      >
        <Pillar
          number="01"
          title="Soberanía"
          body="El modelo corre localmente en una máquina del Estado. Tus consultas no salen del servidor; no las leen Anthropic, OpenAI ni nadie más."
        />
        <Pillar
          number="02"
          title="Verificabilidad"
          body="Cada cifra es reproducible y cada dataset citado es clicable. Si dudas, abre la fuente original y compruébalo."
        />
        <Pillar
          number="03"
          title="Interoperabilidad"
          body="Las mismas herramientas se exponen como MCP server estándar. Cualquier cliente compatible (Claude, Gemini, otros) puede consumirlas."
        />
      </section>
    </div>
  );
}

function Pillar({
  number,
  title,
  body,
}: {
  number: string;
  title: string;
  body: string;
}) {
  return (
    <article>
      <span
        className="kicker"
        style={{ display: "block", marginBlockEnd: 8 }}
      >
        {number} · Pilar
      </span>
      <h3 style={{ fontFamily: "var(--font-serif)", fontSize: "var(--type-h3)", margin: "0 0 12px 0" }}>
        {title}
      </h3>
      <p
        style={{
          margin: 0,
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body)",
          color: "var(--ink-2)",
          lineHeight: 1.6,
        }}
      >
        {body}
      </p>
    </article>
  );
}
