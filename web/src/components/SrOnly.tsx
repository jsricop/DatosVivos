/**
 * `sr-only` helper para texto solo accesible a lectores de pantalla.
 * Tailwind v4 no incluye esta utility por defecto en nuestro setup,
 * así que la definimos aquí.
 */

import type { ReactNode } from "react";

const SR_ONLY: React.CSSProperties = {
  position: "absolute",
  width: 1,
  height: 1,
  padding: 0,
  margin: -1,
  overflow: "hidden",
  clip: "rect(0, 0, 0, 0)",
  whiteSpace: "nowrap",
  border: 0,
};

export function SrOnly({ children }: { children: ReactNode }) {
  return <span style={SR_ONLY}>{children}</span>;
}
