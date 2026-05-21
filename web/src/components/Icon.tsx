/**
 * Set de iconos MVP de DatosVivos (BRAND.md §6.2).
 *
 * Reglas no negociables:
 * - currentColor en stroke (heredan el color del contexto)
 * - viewBox 24x24, stroke-width 1.5, linecap square, linejoin miter
 * - Outline only (sin fill)
 * - Cero emojis en cualquier UI productiva
 */

import type { SVGProps } from "react";

export type IconName =
  | "search"
  | "filter"
  | "mic"
  | "mic-off"
  | "speaker"
  | "speaker-off"
  | "map"
  | "table"
  | "chart-bars"
  | "chart-line"
  | "external-link"
  | "expand"
  | "collapse"
  | "close"
  | "contrast"
  | "sun"
  | "moon"
  | "type-size"
  | "arrow-right"
  | "enter"
  | "menu"
  | "download"
  | "copy";

type IconProps = SVGProps<SVGSVGElement> & {
  name: IconName;
  size?: number;
  title?: string;
};

const PATHS: Record<IconName, string> = {
  search:
    "M10.5 4a6.5 6.5 0 1 0 0 13 6.5 6.5 0 0 0 0-13Zm5 12 4.5 4.5",
  filter:
    "M3 5h18M6 11h12M10 17h4",
  mic:
    "M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3ZM5 11a7 7 0 0 0 14 0M12 18v3M9 21h6",
  "mic-off":
    "M3 3l18 18M9 9v3a3 3 0 0 0 5.12 2.12M15 12V6a3 3 0 0 0-5.66-1.42M5 11a7 7 0 0 0 .92 3.49M19 11a7 7 0 0 1-3.66 6.15M12 18v3M9 21h6",
  speaker:
    "M4 9v6h4l5 4V5L8 9H4Z M16 8a5 5 0 0 1 0 8 M19 5a9 9 0 0 1 0 14",
  "speaker-off":
    "M4 9v6h4l5 4V5L8 9H4Z M16 9l5 6 M21 9l-5 6",
  map: "M3 6v15l6-3 6 3 6-3V3l-6 3-6-3-6 3Z M9 3v15 M15 6v15",
  table:
    "M3 5h18v14H3z M3 10h18 M9 5v14 M15 5v14",
  "chart-bars":
    "M5 21V11 M11 21V5 M17 21v-7 M3 21h18",
  "chart-line":
    "M3 18l5-6 4 3 8-10 M3 21h18",
  "external-link":
    "M5 5h6 M5 5v6 M5 5l9 9 M14 5h5v5",
  expand:
    "M4 4h6 M4 4v6 M20 4h-6 M20 4v6 M4 20h6 M4 20v-6 M20 20h-6 M20 20v-6",
  collapse:
    "M10 4v6h-6 M14 4v6h6 M10 20v-6h-6 M14 20v-6h6",
  close: "M5 5l14 14 M19 5l-14 14",
  contrast:
    "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z M12 3v18 M12 3a9 9 0 0 1 0 18",
  sun:
    "M12 7a5 5 0 1 0 0 10 5 5 0 0 0 0-10Z M12 2v2 M12 20v2 M4.93 4.93l1.41 1.41 M17.66 17.66l1.41 1.41 M2 12h2 M20 12h2 M4.93 19.07l1.41-1.41 M17.66 6.34l1.41-1.41",
  moon:
    "M21 12.79A9 9 0 1 1 11.21 3a7 7 0 0 0 9.79 9.79Z",
  "type-size":
    "M5 19l4-12 4 12 M6 15h6 M14 11l3-7 3 7 M14.6 13h4.8",
  "arrow-right": "M5 12h14 M13 6l6 6-6 6",
  enter: "M3 12l5-5 M3 12l5 5 M3 12h13a4 4 0 0 0 4-4V4",
  menu: "M4 7h16 M4 12h16 M4 17h16",
  download: "M12 3v12 M7 11l5 5 5-5 M4 19h16",
  copy: "M8 8h10v12H8z M5 5h10v3 M5 5v10h3",
};

export function Icon({ name, size = 20, title, ...rest }: IconProps) {
  const path = PATHS[name];
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="square"
      strokeLinejoin="miter"
      role={title ? "img" : "presentation"}
      aria-hidden={title ? undefined : true}
      aria-label={title}
      focusable="false"
      {...rest}
    >
      {title ? <title>{title}</title> : null}
      <path d={path} />
    </svg>
  );
}
