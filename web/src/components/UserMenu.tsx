import Link from "next/link";

import { auth } from "@/lib/auth";

/**
 * Widget en el Header — si hay sesión, muestra abbrev + link a /tablero.
 * Si no, muestra "Acceso institucional" como link a /login.
 *
 * Server component: la sesión se lee server-side y la UI se renderiza con
 * el resultado. No requiere hidratación cliente para la lectura inicial.
 */
export async function UserMenu() {
  const session = await auth();

  if (!session?.user?.email) {
    return (
      <Link
        href="/login"
        className="font-sans text-body-sm text-ink-2 focus-ring"
      >
        Acceso institucional
      </Link>
    );
  }

  const label = session.user.entityAbbrev ?? "Mi tablero";
  return (
    <Link
      href="/tablero"
      className="inline-flex items-center rounded-[var(--radius-1)] border border-accent px-3 py-1.5 font-mono text-caption uppercase tracking-[0.08em] text-accent no-underline hover:bg-bg-overlay focus-ring"
      title={`Sesión: ${session.user.email}`}
    >
      {label}
    </Link>
  );
}
