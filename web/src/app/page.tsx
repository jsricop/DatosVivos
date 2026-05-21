import Link from "next/link";

import { HomeSearchPanel } from "@/components/HomeSearchPanel";
import { Wordmark } from "@/components/Wordmark";
import { fetchPopular, fetchSuggest } from "@/lib/api";
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
    <div className="container-narrow flex flex-col gap-12 py-12">
      <section className="flex flex-col gap-6">
        <Wordmark asHeading size="display" />
        <p className="m-0 max-w-[32ch] font-serif italic text-h2 font-normal leading-tight text-ink-2">
          Datos del Estado, en tus palabras.
        </p>
        <p className="m-0 max-w-[60ch] font-sans text-body-lg text-ink-2 leading-[1.55]">
          Agente de IA con modelo local sobre{" "}
          <a
            href="https://www.datos.gov.co"
            target="_blank"
            rel="noopener noreferrer"
            className="focus-ring"
          >
            datos.gov.co
          </a>
          . Cada cifra que ves está calculada con{" "}
          <code className="font-mono">pandas</code> sobre los datos reales del
          dataset citado. Cero cifras inventadas, trazabilidad por enlace.
        </p>
      </section>

      <HomeSearchPanel chips={chips} />

      <section className="hairline-top pt-8">
        <h2 className="text-kicker mb-4">Lo más consultado esta semana</h2>
        {popular.length > 0 ? (
          <ol className="list-none grid gap-3">
            {popular.map((p, i) => (
              <li
                key={`${p.question}-${i}`}
                className="grid grid-cols-[auto_1fr_auto] gap-4 items-baseline py-2 hairline-bottom"
              >
                <span className="font-mono [font-variant-numeric:tabular-nums] text-body text-accent font-medium">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Link
                  href={`/buscar?q=${encodeURIComponent(p.question)}`}
                  className="font-serif text-body-lg text-ink focus-ring"
                >
                  {p.question}
                </Link>
                <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted [font-variant-numeric:tabular-nums]">
                  {p.count} consultas
                </span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="font-sans text-body-sm text-ink-muted max-w-[60ch]">
            Aún no hay consultas suficientes para componer este ranking.
            Empieza haciendo tu primera pregunta — la telemetría es anónima y
            se queda en la máquina del Estado.
          </p>
        )}
      </section>

      <section className="hairline-top pt-8 grid gap-6 grid-cols-[repeat(auto-fit,minmax(260px,1fr))]">
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

function Pillar({ number, title, body }: { number: string; title: string; body: string }) {
  return (
    <article>
      <span className="text-kicker block mb-2">{number} · Pilar</span>
      <h3 className="font-serif text-h3 m-0 mb-3">{title}</h3>
      <p className="m-0 font-sans text-body text-ink-2 leading-relaxed">{body}</p>
    </article>
  );
}
