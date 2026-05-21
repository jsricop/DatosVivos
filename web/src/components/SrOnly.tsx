/**
 * `sr-only` helper para texto solo accesible a lectores de pantalla.
 * Reusa la clase `.sr-only` declarada en globals.css.
 */

import type { ReactNode } from "react";

export function SrOnly({ children }: { children: ReactNode }) {
  return <span className="sr-only">{children}</span>;
}
