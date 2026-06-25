"use client";

import { useRouter } from "next/navigation";
import {
  type FormEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { Icon } from "@/components/Icon";
import { useReducedMotion } from "@/lib/motion";

type HeroSearchProps = {
  initialValue?: string;
  /** Lista de ejemplos para el placeholder rotativo. Si vacío, usa defaults. */
  placeholders?: string[];
  /** Pre-fills query string adicional (chips activos) al hacer submit. */
  extraQuery?: Record<string, string | string[]>;
  /** Si true, ocupa el ancho display (home); si false, ancho header. */
  size?: "display" | "compact";
};

const DEFAULT_PLACEHOLDERS = [
  "¿Cuántos colegios públicos hay en Boyacá?",
  "¿Tendencia de matrícula en Cundinamarca 2018-2024?",
  "¿Cobertura de vacunación contra fiebre amarilla?",
  "¿Top 10 municipios con más estudiantes matriculados?",
  "¿Cuántos contratos firmó la ANI en 2024?",
];

/**
 * HeroSearch (BRAND.md §8.1).
 *
 * - Placeholder rotativo cada 6 s (pausa en focus/typing — PR3 añade prefers-reduced-motion).
 * - Submit → /buscar?q=... con extraQuery preservado.
 * - Botón "Buscar" con glifo `↵` + label visible.
 * - Atajo `/` para enfocar desde cualquier parte de la página.
 */
export function HeroSearch({
  initialValue = "",
  placeholders = DEFAULT_PLACEHOLDERS,
  extraQuery = {},
  size = "display",
}: HeroSearchProps) {
  const router = useRouter();
  const [q, setQ] = useState(initialValue);
  const [phIndex, setPhIndex] = useState(0);
  const [isFocused, setIsFocused] = useState(false);
  const reducedMotion = useReducedMotion();
  const inputRef = useRef<HTMLInputElement>(null);

  // Permite que el padre "siembre" la caja (ej. chips de ejemplo o dictado de
  // voz): cuando initialValue cambia, sincronizamos el valor y enfocamos para
  // que el ciudadano vea el texto listo y solo pulse Buscar.
  useEffect(() => {
    if (initialValue) {
      setQ(initialValue);
      inputRef.current?.focus();
    }
  }, [initialValue]);

  useEffect(() => {
    if (reducedMotion) return; // respeta prefers-reduced-motion (BRAND.md §5.5)
    if (placeholders.length <= 1) return;
    if (q.length > 0) return; // pausa cuando el usuario está escribiendo
    if (isFocused) return; // pausa cuando el campo está enfocado
    const id = window.setInterval(() => {
      setPhIndex((i) => (i + 1) % placeholders.length);
    }, 6000);
    return () => window.clearInterval(id);
  }, [placeholders.length, q.length, isFocused, reducedMotion]);

  useEffect(() => {
    function focusOnSlash(e: KeyboardEvent) {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", focusOnSlash);
    return () => window.removeEventListener("keydown", focusOnSlash);
  }, []);

  const placeholder = useMemo(
    () => placeholders[phIndex] ?? placeholders[0] ?? "",
    [phIndex, placeholders],
  );

  const [isMapping, setIsMapping] = useState(false);

  const onSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const trimmed = q.trim();
      if (!trimmed) {
        inputRef.current?.focus();
        return;
      }
      // Fase 2: intentar mapear el NL a chips antes de navegar. Si el
      // mapper devuelve al menos tema o tipo, navego al path de chips;
      // si no, fallback al path libre (?q=...) como antes.
      setIsMapping(true);
      let chipsParams: URLSearchParams | null = null;
      try {
        const res = await fetch("/api/chips/from-nl", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ q: trimmed }),
        });
        if (res.ok) {
          const j = (await res.json()) as {
            tema?: string | null;
            tipo?: string | null;
            territorio?: string | null;
            entidad?: string | null;
            refinador?: string | null;
          };
          // Aceptamos el mapeo si hay al menos UN chip inferido —
          // basta TIPO o TEMA para activar el flujo de chips.
          const hasAnyChip =
            !!(j.tema || j.tipo || j.territorio || j.entidad);
          if (hasAnyChip) {
            chipsParams = new URLSearchParams();
            if (j.tema) chipsParams.set("tema", j.tema);
            if (j.tipo) chipsParams.set("tipo", j.tipo);
            if (j.territorio) chipsParams.set("territorio", j.territorio);
            if (j.entidad) chipsParams.set("entidad", j.entidad);
            if (j.refinador) chipsParams.set("refinador", j.refinador);
          }
        }
      } catch {
        // Mapping falló → fallback al path libre.
      } finally {
        setIsMapping(false);
      }

      const params = chipsParams ?? new URLSearchParams({ q: trimmed });
      for (const [key, val] of Object.entries(extraQuery)) {
        if (Array.isArray(val)) {
          for (const v of val) params.append(key, v);
        } else if (val) {
          params.set(key, val);
        }
      }
      router.push(`/buscar?${params.toString()}`);
    },
    [q, extraQuery, router],
  );

  const isDisplay = size === "display";

  return (
    <form
      onSubmit={onSubmit}
      role="search"
      aria-label="Buscar en datos.gov.co"
      className="flex items-stretch w-full overflow-hidden rounded-[var(--radius-2)] border border-hairline bg-bg-elev focus-within:border-accent transition-colors"
    >
      <label htmlFor="hero-search-input" className="sr-only">
        Escribe tu pregunta
      </label>
      <span aria-hidden="true" className="inline-flex items-center px-5 text-ink-2">
        <Icon name="search" size={isDisplay ? 24 : 20} />
      </span>
      <input
        id="hero-search-input"
        ref={inputRef}
        type="text"
        autoComplete="off"
        autoCorrect="off"
        spellCheck={false}
        value={q}
        onChange={(e) => setQ(e.target.value)}
        onFocus={() => setIsFocused(true)}
        onBlur={() => setIsFocused(false)}
        placeholder={placeholder}
        aria-label="Pregunta en lenguaje natural"
        className={[
          "datosvivos-search-input flex-1 min-w-0 px-2 bg-transparent font-sans text-ink",
          isDisplay ? "py-6 text-h3" : "py-[14px] text-body-lg",
        ].join(" ")}
      />
      <button
        type="submit"
        disabled={isMapping}
        aria-label="Ejecutar búsqueda"
        className="inline-flex items-center gap-2.5 px-6 bg-accent hover:bg-accent-2 text-bg font-sans text-body font-bold tracking-[0.2px] transition-colors focus-ring disabled:opacity-60"
      >
        <span>{isMapping ? "Interpretando…" : "Buscar"}</span>
        <Icon name="enter" size={18} aria-hidden />
      </button>
    </form>
  );
}
