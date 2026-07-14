"use client";

import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/Icon";
import {
  applyTheme,
  isTheme,
  readThemeFromStorage,
  type Theme,
  writeThemeToStorage,
} from "@/lib/theme";

type Option = { value: Theme; label: string; icon: IconName };

const OPTIONS: Option[] = [
  { value: "light", label: "Claro", icon: "sun" },
  { value: "dark", label: "Oscuro", icon: "moon" },
  { value: "contrast-light", label: "Alto contraste", icon: "contrast" },
];

/**
 * ColorModeToggle (BRAND.md §8.11).
 *
 * - Label visible "Apariencia" (desktop) para que el control se lea como
 *   selector y no como tres palabras sueltas.
 * - 3 modos seleccionables con icono distintivo por modo (sun/moon/contrast).
 *   El cuarto (contrast-dark) se accede desde /accesibilidad con sub-selector.
 * - Persistido en localStorage bajo datosvivos:theme.
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

  // Sin label visible: los tres botones con icono + texto ya se leen como
  // selector; "APARIENCIA" era ruido en la barra (2026-07-13).
  return (
    <div className="flex items-center gap-3">
      <div
        role="group"
        aria-label="Apariencia — modo de color"
        className="inline-flex items-center border border-hairline bg-bg-elev p-[2px] rounded-[var(--radius-1)]"
      >
        {OPTIONS.map((opt) => {
          const isActive = currentValue === opt.value;
          const stateClass = isActive
            ? "bg-accent text-bg"
            : "bg-transparent text-ink-2 hover:text-ink";
          return (
            <button
              key={opt.value}
              type="button"
              onClick={() => pick(opt.value)}
              aria-pressed={isActive}
              title={`Modo ${opt.label.toLowerCase()}`}
              className={`${stateClass} inline-flex items-center gap-1.5 px-2.5 py-1.5 font-mono text-[length:var(--type-kicker)] font-medium uppercase tracking-[0.08em] transition-colors focus-ring`}
            >
              <Icon name={opt.icon} size={14} />
              <span className="hidden md:inline">{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
