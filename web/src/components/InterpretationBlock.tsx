/**
 * InterpretationBlock — "Esto entendí" (ADR-022 Fase 5).
 *
 * Muestra, ANTES de la cifra, cómo el motor interpretó la pregunta: el dataset
 * elegido, el territorio/filtros, las columnas usadas y el estado de verificación
 * de la consulta. Es informativo (no bloquea): si el ciudadano ve que entendimos
 * mal, reformula. Refuerza la transparencia de ADR-018 (SoQL visible) un paso
 * antes: no solo "qué consulté" sino "qué entendí que me pediste".
 */

import { CheckIcon, WarnIcon } from "@/components/icons";

type Filtro = { campo: string; valor?: string | null; etiqueta?: string | null };

export type Interpretation = {
  intent?: string;
  dataset?: { id: string; name: string; entity?: string | null } | null;
  filtros: Filtro[];
  columnasUsadas: string[];
  verificacion: { passed: boolean; repairs: number; fallback?: string | null };
};

const INTENT_LABEL: Record<string, string> = {
  search: "Catálogo",
  descriptive: "Descripción",
  comparative: "Comparativa",
  temporal: "Tendencia",
  cross_source: "Cruce multi-fuente",
};

function VerificationBadge({
  passed,
  fallback,
}: {
  passed: boolean;
  fallback?: string | null;
}) {
  if (passed && fallback === "template") {
    return (
      <span className="inline-flex items-center gap-1.5 text-caption text-ok">
        <CheckIcon /> Verificada (plantilla determinista)
      </span>
    );
  }
  if (passed) {
    return (
      <span className="inline-flex items-center gap-1.5 text-caption text-ok">
        <CheckIcon /> Consulta verificada
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1.5 text-caption text-warn">
      <WarnIcon /> Consulta sin verificar del todo
    </span>
  );
}

export function InterpretationBlock({ data }: { data: Interpretation }) {
  const territorios = data.filtros.filter((f) => f.campo === "territorio" && f.etiqueta);
  return (
    <section className="surface-card border-l-4 border-l-accent p-4 flex flex-col gap-2">
      <span className="text-kicker text-ink-2">Esto entendí</span>
      <div className="flex flex-col gap-1 text-body-sm text-ink-2">
        {data.dataset ? (
          <p className="m-0">
            <span className="text-ink-muted">Fuente: </span>
            <span className="text-ink">{data.dataset.name}</span>
            {data.dataset.entity ? (
              <span className="text-ink-muted"> · {data.dataset.entity}</span>
            ) : null}
          </p>
        ) : null}
        <p className="m-0">
          <span className="text-ink-muted">Tipo de consulta: </span>
          {data.intent ? INTENT_LABEL[data.intent] ?? data.intent : "—"}
        </p>
        {territorios.length > 0 ? (
          <p className="m-0 flex flex-wrap items-center gap-2">
            <span className="text-ink-muted">Territorio:</span>
            {territorios.map((t, i) => (
              <span
                key={i}
                className="rounded-[var(--radius-1)] bg-bg-elev px-2 py-0.5 text-caption text-ink"
              >
                {t.etiqueta}
              </span>
            ))}
          </p>
        ) : null}
        {data.columnasUsadas.length > 0 ? (
          <p className="m-0">
            <span className="text-ink-muted">Columnas usadas: </span>
            <span className="font-mono text-[length:var(--type-caption)]">
              {data.columnasUsadas.join(", ")}
            </span>
          </p>
        ) : null}
      </div>
      <VerificationBadge
        passed={data.verificacion.passed}
        fallback={data.verificacion.fallback}
      />
    </section>
  );
}
