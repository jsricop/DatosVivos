import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/**
 * Middleware edge-runtime que protege rutas auth-required.
 *
 * Diseño: chequea solo la PRESENCIA de la cookie de sesión next-auth.
 * No valida el JWT ni consulta DB — eso ocurre en server components que
 * sí pueden usar Node APIs (`pg`, `stream`). Edge runtime no soporta
 * módulos Node, por eso NO importamos `@/lib/auth` aquí (que usa `pg`).
 *
 * Hoy protege: `/tablero`. Si no hay cookie de sesión → redirect a
 * `/login?callbackUrl=…`. La validación real de la sesión la hace el
 * server component en `/tablero/page.tsx`.
 */
export default function middleware(req: NextRequest) {
  const pathname = req.nextUrl.pathname;

  if (pathname.startsWith("/tablero")) {
    const sessionToken =
      req.cookies.get("authjs.session-token") ??
      req.cookies.get("__Secure-authjs.session-token") ??
      req.cookies.get("next-auth.session-token") ??
      req.cookies.get("__Secure-next-auth.session-token");

    if (!sessionToken) {
      const loginUrl = new URL("/login", req.nextUrl);
      loginUrl.searchParams.set("callbackUrl", pathname);
      return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/tablero/:path*"],
};
