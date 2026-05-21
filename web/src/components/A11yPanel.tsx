"use client";

import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/Icon";
import {
  applyFontScale,
  applyTheme,
  FONT_SCALES,
  type FontScale,
  isTheme,
  readFontScaleFromStorage,
  readThemeFromStorage,
  type Theme,
  THEMES,
  writeFontScaleToStorage,
  writeThemeToStorage,
} from "@/lib/theme";

const THEME_LABEL: Record<Theme, string> = {
  light: "Claro / papel",
  dark: "Oscuro / tinta",
  "contrast-light": "Alto contraste — sobre blanco",
  "contrast-dark": "Alto contraste — sobre negro",
  auto: "Automático según sistema",
};

/**
 * A11yPanel (BRAND.md §8.12) — controles centralizados de accesibilidad.
 */
export function A11yPanel() {
  const [mounted, setMounted] = useState(false);
  const [theme, setTheme] = useState<Theme>("light");
  const [scale, setScale] = useState<FontScale>(1);

  useEffect(() => {
    setTheme(readThemeFromStorage());
    setScale(readFontScaleFromStorage());
    setMounted(true);
  }, []);

  function pickTheme(next: string) {
    if (!isTheme(next)) return;
    setTheme(next);
    applyTheme(next);
    writeThemeToStorage(next);
  }

  function pickScale(value: number) {
    const allowed = FONT_SCALES.find((s) => s.value === value);
    if (!allowed) return;
    setScale(allowed.value);
    applyFontScale(allowed.value);
    writeFontScaleToStorage(allowed.value);
  }

  if (!mounted) return null;

  return (
    <section aria-label="Controles de accesibilidad" className="grid gap-6">
      <Group title="Modo de color" icon="contrast">
        <div className="flex flex-col gap-2">
          {THEMES.map((t) => (
            <label key={t} className="inline-flex items-baseline gap-3 font-sans text-body cursor-pointer">
              <input
                type="radio"
                name="theme"
                value={t}
                checked={theme === t}
                onChange={(e) => pickTheme(e.target.value)}
              />
              <span>{THEME_LABEL[t]}</span>
            </label>
          ))}
        </div>
      </Group>

      <Group title="Tamaño tipográfico" icon="type-size">
        <div className="flex flex-col gap-2">
          {FONT_SCALES.map((s) => (
            <label key={s.value} className="inline-flex items-baseline gap-3 font-sans text-body cursor-pointer">
              <input
                type="radio"
                name="font-scale"
                value={s.value}
                checked={scale === s.value}
                onChange={(e) => pickScale(Number(e.target.value))}
              />
              <span>
                {s.label}{" "}
                <span className="font-mono text-[length:var(--type-kicker)] text-ink-muted">
                  ({s.caption})
                </span>
              </span>
            </label>
          ))}
        </div>
      </Group>

      <Group title="Voz" icon="speaker">
        <p className="m-0 font-sans text-body text-ink-2 leading-relaxed">
          La entrada por voz (STT) y la lectura en voz alta (TTS) se controlan
          desde cada vista. Funcionan con el reconocimiento nativo del
          navegador en español de Colombia. Compatibilidad: Chrome y Edge
          óptimos; Safari sin STT.
        </p>
      </Group>

      <Group title="Atajos de teclado" icon="menu">
        <ul className="flex flex-col gap-1.5">
          <ShortcutRow keys="Tab" description="Navegar entre controles" />
          <ShortcutRow keys="/" description="Enfocar el buscador" />
          <ShortcutRow keys="Esc" description="Cerrar paneles y diálogos" />
          <ShortcutRow keys="Enter" description="Activar el botón enfocado / enviar consulta" />
        </ul>
      </Group>
    </section>
  );
}

function Group({
  title,
  icon,
  children,
}: {
  title: string;
  icon: IconName;
  children: React.ReactNode;
}) {
  return (
    <article className="surface-elev p-6">
      <header className="flex items-center gap-2.5 mb-4">
        <Icon name={icon} size={20} aria-hidden />
        <h3 className="m-0 font-sans text-h4 font-semibold">{title}</h3>
      </header>
      {children}
    </article>
  );
}

function ShortcutRow({ keys, description }: { keys: string; description: string }) {
  return (
    <li className="flex items-baseline gap-3">
      <kbd className="inline-block border border-hairline-strong px-2 py-px font-mono text-caption bg-bg text-ink min-w-[2.4em] text-center">
        {keys}
      </kbd>
      <span>{description}</span>
    </li>
  );
}
