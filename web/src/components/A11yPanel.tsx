"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";
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

  if (!mounted) {
    return null;
  }

  return (
    <section
      aria-label="Controles de accesibilidad"
      style={{
        display: "grid",
        gap: "var(--space-5)",
      }}
    >
      <Group title="Modo de color" icon="contrast">
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {THEMES.map((t) => (
            <label key={t} style={radioRow}>
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
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {FONT_SCALES.map((s) => (
            <label key={s.value} style={radioRow}>
              <input
                type="radio"
                name="font-scale"
                value={s.value}
                checked={scale === s.value}
                onChange={(e) => pickScale(Number(e.target.value))}
              />
              <span>
                {s.label}{" "}
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--type-kicker)",
                    color: "var(--ink-muted)",
                  }}
                >
                  ({s.caption})
                </span>
              </span>
            </label>
          ))}
        </div>
      </Group>

      <Group title="Voz" icon="speaker">
        <p style={pStyle}>
          La entrada por voz (STT) y la lectura en voz alta (TTS) se controlan
          desde cada vista. Funcionan con el reconocimiento nativo del
          navegador en español de Colombia. Compatibilidad: Chrome y Edge
          óptimos; Safari sin STT.
        </p>
      </Group>

      <Group title="Atajos de teclado" icon="menu">
        <ul style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <li style={kbdRow}>
            <kbd style={kbdStyle}>Tab</kbd>
            <span>Navegar entre controles</span>
          </li>
          <li style={kbdRow}>
            <kbd style={kbdStyle}>/</kbd>
            <span>Enfocar el buscador</span>
          </li>
          <li style={kbdRow}>
            <kbd style={kbdStyle}>Esc</kbd>
            <span>Cerrar paneles y diálogos</span>
          </li>
          <li style={kbdRow}>
            <kbd style={kbdStyle}>Enter</kbd>
            <span>Activar el botón enfocado / enviar consulta</span>
          </li>
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
  icon: "contrast" | "type-size" | "speaker" | "menu";
  children: React.ReactNode;
}) {
  return (
    <article
      style={{
        border: "1px solid var(--hairline)",
        padding: "var(--space-5)",
        background: "var(--bg-elev)",
      }}
    >
      <header
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          marginBlockEnd: 16,
        }}
      >
        <Icon name={icon} size={20} aria-hidden />
        <h3
          style={{
            margin: 0,
            fontFamily: "var(--font-sans)",
            fontSize: "var(--type-h4)",
            fontWeight: 600,
          }}
        >
          {title}
        </h3>
      </header>
      {children}
    </article>
  );
}

const radioRow: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "baseline",
  gap: 12,
  fontFamily: "var(--font-sans)",
  fontSize: "var(--type-body)",
  cursor: "pointer",
};

const kbdRow: React.CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 12,
};

const kbdStyle: React.CSSProperties = {
  display: "inline-block",
  border: "1px solid var(--hairline-strong)",
  padding: "1px 8px",
  fontFamily: "var(--font-mono)",
  fontSize: "var(--type-caption)",
  background: "var(--bg)",
  color: "var(--ink)",
  minInlineSize: "2.4em",
  textAlign: "center" as const,
};

const pStyle: React.CSSProperties = {
  margin: 0,
  fontFamily: "var(--font-sans)",
  fontSize: "var(--type-body)",
  color: "var(--ink-2)",
  lineHeight: 1.6,
};
