"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

/**
 * Ítem de la navegación primaria (BRAND.md §8.12, 2026-07-13).
 *
 * Antes eran palabras sueltas sin affordance: no se leían como opciones.
 * Ahora cada ítem es una "pastilla" con hover visible y la página ACTUAL
 * queda marcada (fondo elevado + acento + aria-current) — el visitante
 * siempre sabe dónde está.
 */
export function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname?.startsWith(href) ?? false;

  return (
    <Link
      href={href}
      aria-current={isActive ? "page" : undefined}
      className={[
        "rounded-[var(--radius-1)] border px-3 py-1.5 font-sans text-body-sm no-underline transition-colors focus-ring",
        isActive
          ? "border-hairline bg-bg-elev font-semibold text-accent"
          : "border-transparent text-ink-2 hover:border-hairline hover:bg-bg-elev hover:text-ink",
      ].join(" ")}
    >
      {children}
    </Link>
  );
}
