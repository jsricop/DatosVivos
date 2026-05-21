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
  "¿Tendencia de homicidios en Cali 2018-2024?",
  "¿Cobertura de vacunación contra fiebre amarilla?",
  "¿Top 10 municipios con más estudiantes matriculados?",
  "¿Cuántos contratos firmó la ANI en 2024?",
];

/**
 * HeroSearch (BRAND.md §8.1).
 *
 * - Placeholder rotativo cada 6s.
 * - Submit → /buscar?q=... con extraQuery preservado.
 * - Botón "Buscar" con glifo `↵` + label visible (no solo icono).
 * - STT opcional (componente hermano `SpeechInput` lo conecta).
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
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (placeholders.length <= 1) return;
    const id = window.setInterval(() => {
      setPhIndex((i) => (i + 1) % placeholders.length);
    }, 6000);
    return () => window.clearInterval(id);
  }, [placeholders.length]);

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

  const onSubmit = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      const trimmed = q.trim();
      if (!trimmed) {
        inputRef.current?.focus();
        return;
      }
      const params = new URLSearchParams({ q: trimmed });
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
      style={{
        display: "flex",
        alignItems: "stretch",
        gap: 0,
        width: "100%",
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
        transition:
          "border-color var(--duration-fast) var(--easing-standard)",
      }}
    >
      <label htmlFor="hero-search-input" className="sr-only">
        Escribe tu pregunta
      </label>
      <span
        aria-hidden="true"
        style={{
          display: "inline-flex",
          alignItems: "center",
          paddingInline: 20,
          color: "var(--ink-2)",
        }}
      >
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
        placeholder={placeholder}
        aria-label="Pregunta en lenguaje natural"
        style={{
          flex: 1,
          paddingBlock: isDisplay ? 24 : 14,
          paddingInline: 8,
          fontFamily: "var(--font-serif)",
          fontSize: isDisplay ? "var(--type-h3)" : "var(--type-body-lg)",
          fontWeight: 400,
          color: "var(--ink)",
          background: "transparent",
          minWidth: 0,
        }}
      />
      <button
        type="submit"
        aria-label="Ejecutar búsqueda"
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: 10,
          paddingInline: 24,
          background: "var(--ink)",
          color: "var(--bg)",
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body)",
          fontWeight: 600,
          letterSpacing: 0.2,
        }}
      >
        <span>Buscar</span>
        <Icon name="enter" size={18} aria-hidden />
      </button>
    </form>
  );
}
