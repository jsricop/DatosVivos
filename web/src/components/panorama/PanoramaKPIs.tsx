"use client";

import { CountUp } from "@/components/panorama/CountUp";
import type { PanoramaStats } from "@/lib/types";

const fmtInt = (n: number) => Math.round(n).toLocaleString("es-CO");
const fmtPct = (n: number) => `${Math.round(n)}%`;

/**
 * Fila de KPIs del panorama nacional (ADR-023). Client component solo por el
 * count-up; los valores llegan server-fetched y están completos en el HTML.
 */
export function PanoramaKPIs({ stats }: { stats: PanoramaStats }) {
  const pctFrescos =
    stats.total > 0 ? (100 * stats.semaforo.verde) / stats.total : 0;
  const consultables =
    stats.acceso.directo + stats.acceso.requiere_herramienta;
  const pctConsultables =
    stats.total > 0 ? (100 * consultables) / stats.total : 0;

  const cards: Array<{ label: string; value: number; format: (n: number) => string; hint?: string }> = [
    { label: "Datasets en el catálogo", value: stats.total, format: fmtInt },
    { label: "Entidades publicadoras", value: stats.n_entidades, format: fmtInt },
    {
      label: "Actualizados al día",
      value: pctFrescos,
      format: fmtPct,
      hint: "según la frecuencia que cada entidad declara",
    },
    {
      label: "Consultables como tabla",
      value: pctConsultables,
      format: fmtPct,
      hint: "en línea o descargando el archivo",
    },
  ];

  return (
    <section aria-label="Cifras del catálogo en vivo">
      <ul className="grid grid-cols-2 md:grid-cols-4 gap-3 list-none m-0 p-0">
        {cards.map((c) => (
          <li key={c.label} className="surface-elev p-6 flex flex-col gap-2">
            <span
              className="font-mono [font-variant-numeric:tabular-nums] text-accent font-medium leading-none"
              style={{ fontSize: "clamp(1.75rem, 4vw, 2.75rem)" }}
            >
              <CountUp value={c.value} format={c.format} />
            </span>
            <span className="text-kicker">{c.label}</span>
            {c.hint ? (
              <span className="font-sans text-caption text-ink-muted">
                {c.hint}
              </span>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
