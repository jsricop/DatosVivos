/**
 * Hooks de accesibilidad para reduced-motion y escala tipográfica.
 *
 * `useReducedMotion()` — true si el usuario tiene `prefers-reduced-motion: reduce`.
 *   Reactivo al cambio de preferencia del sistema.
 *
 * `useUserScale()` — factor (0.9 / 1 / 1.15 / 1.3) leído de `--user-scale`
 *   en `<html>`. Útil para escalar componentes SVG cuyo `<font-size>` HTML
 *   no afecta su altura nativa (charts, mapas).
 */

"use client";

import { useEffect, useState } from "react";

import { FONT_SCALE_STORAGE_KEY } from "@/lib/theme";

export function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return;
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(mql.matches);
    const handler = (e: MediaQueryListEvent) => setReduced(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);
  return reduced;
}

function readScale(): number {
  if (typeof window === "undefined") return 1;
  try {
    const raw = window.localStorage.getItem(FONT_SCALE_STORAGE_KEY);
    const parsed = raw ? Number(raw) : 1;
    if (!Number.isFinite(parsed) || parsed < 0.5 || parsed > 2) return 1;
    return parsed;
  } catch {
    return 1;
  }
}

export function useUserScale(): number {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    setScale(readScale());
    function onStorage(e: StorageEvent) {
      if (e.key === FONT_SCALE_STORAGE_KEY) setScale(readScale());
    }
    // El A11yPanel cambia localStorage en la misma pestaña — `storage` event
    // no se dispara para misma pestaña, así que usamos un custom event.
    function onCustom() {
      setScale(readScale());
    }
    window.addEventListener("storage", onStorage);
    window.addEventListener("datosvivos:font-scale", onCustom as EventListener);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("datosvivos:font-scale", onCustom as EventListener);
    };
  }, []);
  return scale;
}
