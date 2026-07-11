"use client";

import { useEffect, useRef, useState } from "react";

import { useReducedMotion } from "@/lib/motion";

/**
 * Revelado único al entrar al viewport (ADR-023, BRAND.md §11.6).
 *
 * Contrato fail-safe: el markup server-rendered SIEMPRE está en su estado
 * final (visible). Este hook, solo con JS hidratado, oculta el elemento un
 * instante (`.is-pending`) y lo revela cuando el 25% entra al viewport.
 * Sin JS o con `prefers-reduced-motion`, nunca se oculta nada.
 *
 * Devuelve `{ ref, revealed }`: aplicar `is-pending` cuando `!revealed`.
 */
export function useRevealOnce<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const reduced = useReducedMotion();
  // Arranca revelado (SSR = estado final); al montar decidimos si ocultar.
  const [revealed, setRevealed] = useState(true);
  const armed = useRef(false);

  useEffect(() => {
    if (reduced || armed.current) return;
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    armed.current = true;

    // Si ya está en viewport al hidratar (above the fold), ocultamos y
    // revelamos en el siguiente frame para que la transición sí ocurra.
    setRevealed(false);
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setRevealed(true);
          io.disconnect();
        }
      },
      { threshold: 0.25 },
    );
    // Doble rAF: garantiza un paint con is-pending antes de revelar.
    requestAnimationFrame(() => requestAnimationFrame(() => io.observe(el)));
    return () => io.disconnect();
  }, [reduced]);

  return { ref, revealed };
}
