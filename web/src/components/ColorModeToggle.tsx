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

  return (
    <div className="flex items-center gap-3">
      <span
        id="color-mode-label"
        className="hidden sm:inline font-mono text-caption text-ink-muted uppercase tracking-[0.08em]"
      >
        Apariencia
      </span>
      <div
        role="group"
        aria-labelledby="color-mode-label"
        aria-label="Modo de color"
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
              <span>{opt.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
