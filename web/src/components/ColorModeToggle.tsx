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
 * - 3 modos seleccionables. El cuarto (contrast-dark) se accede desde
 *   /accesibilidad con un sub-selector A/B.
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
    <div
      role="group"
      aria-label="Modo de color"
      className="inline-flex items-center border border-hairline bg-bg-elev p-[2px] rounded-[var(--radius-1)]"
    >
      {OPTIONS.map((opt) => {
        const isActive = currentValue === opt.value;
        const stateClass = isActive
          ? "bg-ink text-bg"
          : "bg-transparent text-ink-2";
        return (
          <button
            key={opt.value}
            type="button"
            onClick={() => pick(opt.value)}
            aria-pressed={isActive}
            title={`Modo ${opt.label.toLowerCase()}`}
            className={`${stateClass} inline-flex items-center gap-1.5 px-2.5 py-1.5 font-mono text-[length:var(--type-kicker)] font-medium uppercase tracking-[0.08em] transition-colors focus-ring`}
          >
            <Icon name="contrast" size={14} />
            <span>{opt.label}</span>
          </button>
        );
      })}
    </div>
  );
}
