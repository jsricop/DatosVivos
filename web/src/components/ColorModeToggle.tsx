"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
import {
  applyTheme,
  isTheme,
  readThemeFromStorage,
  type Theme,
  writeThemeToStorage,
} from "@/lib/theme";

type Option = { value: Theme; label: string };

const OPTIONS: Option[] = [
  { value: "light", label: "Claro" },
  { value: "dark", label: "Oscuro" },
  { value: "contrast-light", label: "Alto contraste" },
];

/**
 * ColorModeToggle (BRAND.md §8.11).
 *
 * - 3 modos seleccionables. El cuarto (`contrast-dark`) se accede desde
 *   /accesibilidad con un sub-selector A/B sobre la variante alto contraste.
 * - Persistido en localStorage bajo `datosvivos:theme`.
 * - Pre-aplicado anti-FOUC por el script inline en layout.tsx.
 */
export function ColorModeToggle() {
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<Theme>("light");

  useEffect(() => {
    const initial = readThemeFromStorage();
    setTheme(initial);
    setMounted(true);
  }, []);

  function pick(next: Theme) {
    if (!isTheme(next)) return;
    setTheme(next);
    applyTheme(next);
    writeThemeToStorage(next);
  }

  // Evita mismatch SSR/CSR: no mostramos botones activos hasta que montamos.
  const currentValue = mounted ? theme : "light";

  return (
    <div
      role="group"
      aria-label="Modo de color"
      className="inline-flex items-center"
      style={{
        border: "var(--hairline-width) solid var(--hairline)",
        borderRadius: "var(--radius-1)",
        padding: 2,
        background: "var(--bg-elev)",
      }}
    >
      {OPTIONS.map((opt) => {
        const isActive = currentValue === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => pick(opt.value)}
            aria-pressed={isActive}
            title={`Modo ${opt.label.toLowerCase()}`}
            style={{
              padding: "6px 10px",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-kicker)",
              fontWeight: 500,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: isActive ? "var(--bg)" : "var(--ink-2)",
              background: isActive ? "var(--ink)" : "transparent",
              transition: "background var(--duration-fast) var(--easing-standard)",
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
            }}
          >
            <Icon name="contrast" size={14} />
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
