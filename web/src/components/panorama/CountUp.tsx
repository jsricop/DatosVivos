"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "@/lib/motion";

type Props = {
  value: number;
  /** Formateador del valor (default: es-CO con separador de miles). */
  format?: (n: number) => string;
  durationMs?: number;
};

const fmtDefault = (n: number) => Math.round(n).toLocaleString("es-CO");

/**
 * Count-up de revelado de datos (ADR-023). Fail-safe: el valor FINAL está
 * siempre en el HTML server-rendered; el conteo solo lo re-revela tras
 * hidratar, una única vez, al entrar al viewport. `prefers-reduced-motion`
 * o ausencia de JS ⇒ cifra final directa. El span animado es aria-hidden y
 * el valor real vive en un texto sr-only estable (los lectores de pantalla
 * lo anuncian una vez, sin metralleta de números intermedios).
 */
export function CountUp({ value, format = fmtDefault, durationMs = 800 }: Props) {
  const reduced = useReducedMotion();
  const ref = useRef<HTMLSpanElement | null>(null);
  const [display, setDisplay] = useState(value);
  const started = useRef(false);

  useEffect(() => {
    if (reduced || started.current || value <= 0) return;
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;

    const io = new IntersectionObserver(
      (entries) => {
        if (!entries.some((e) => e.isIntersecting) || started.current) return;
        started.current = true;
        io.disconnect();

        const t0 = performance.now();
        setDisplay(0);
        const tick = (t: number) => {
          const p = Math.min(1, (t - t0) / durationMs);
          const eased = 1 - Math.pow(1 - p, 3); // ease-out cúbico
          setDisplay(value * eased);
          if (p < 1) requestAnimationFrame(tick);
          else setDisplay(value);
        };
        requestAnimationFrame(tick);
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduced, value, durationMs]);

  return (
    <>
      <span ref={ref} aria-hidden="true">
        {format(display)}
      </span>
      <span className="sr-only">{format(value)}</span>
    </>
  );
}
