/**
 * Theme management — modos claro / oscuro / alto contraste.
 *
 * Persistido en localStorage bajo `datosvivos:theme`. Aplicado en <html>
 * via `data-theme`. El anti-FOUC vive en `app/layout.tsx` como script inline.
 *
 * Fuente: docs/BRAND.md §3.5
 */

export const THEME_STORAGE_KEY = "datosvivos:theme";

export const THEMES = [
  "light",
  "dark",
  "contrast-light",
  "contrast-dark",
  "auto",
] as const;

export type Theme = (typeof THEMES)[number];

export function isTheme(value: unknown): value is Theme {
  return typeof value === "string" && (THEMES as readonly string[]).includes(value);
}

export function readThemeFromStorage(): Theme {
  if (typeof window === "undefined") return "light";
  try {
    const raw = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(raw) ? raw : "light";
  } catch {
    return "light";
  }
}

export function writeThemeToStorage(theme: Theme): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    /* ignore: storage disabled */
  }
}

export function applyTheme(theme: Theme): void {
  if (typeof document === "undefined") return;
  document.documentElement.setAttribute("data-theme", theme);
}

/**
 * Script inline para anti-FOUC. Se inyecta dentro de <head>.
 * Lee localStorage y aplica data-theme antes del primer render de React.
 */
export const ANTI_FOUC_SCRIPT = `(function(){try{var t=localStorage.getItem('${THEME_STORAGE_KEY}');var valid=['light','dark','contrast-light','contrast-dark','auto'];if(!t||valid.indexOf(t)<0){t='light';}document.documentElement.setAttribute('data-theme',t);}catch(e){document.documentElement.setAttribute('data-theme','light');}})();`;

/** Escala de usuario para tamaño tipográfico (BRAND.md §4.3). */
export const FONT_SCALES = [
  { value: 0.9, label: "Compacto", caption: "90%" },
  { value: 1, label: "Normal", caption: "100%" },
  { value: 1.15, label: "Cómodo", caption: "115%" },
  { value: 1.3, label: "Amplio", caption: "130%" },
] as const;

export type FontScale = (typeof FONT_SCALES)[number]["value"];

export const FONT_SCALE_STORAGE_KEY = "datosvivos:font-scale";

export function readFontScaleFromStorage(): FontScale {
  if (typeof window === "undefined") return 1;
  try {
    const raw = window.localStorage.getItem(FONT_SCALE_STORAGE_KEY);
    const parsed = raw ? Number(raw) : 1;
    return (FONT_SCALES.find((s) => s.value === parsed)?.value ?? 1) as FontScale;
  } catch {
    return 1;
  }
}

export function writeFontScaleToStorage(scale: FontScale): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(FONT_SCALE_STORAGE_KEY, String(scale));
  } catch {
    /* ignore */
  }
}

export function applyFontScale(scale: FontScale): void {
  if (typeof document === "undefined") return;
  document.documentElement.style.setProperty("--user-scale", String(scale));
}

export const ANTI_FOUC_SCALE_SCRIPT = `(function(){try{var s=parseFloat(localStorage.getItem('${FONT_SCALE_STORAGE_KEY}'));if(!isFinite(s)||s<0.5||s>2){s=1;}document.documentElement.style.setProperty('--user-scale',String(s));}catch(e){document.documentElement.style.setProperty('--user-scale','1');}})();`;
