import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

import { auth } from "@/lib/auth";

/**
 * Middleware que protege rutas auth-required.
 *
 * Hoy: solo `/tablero`. Si no hay sesión, redirige a `/login?callbackUrl=…`.
 * Para añadir más rutas protegidas, edita el `matcher` y la condición.
 */
export default auth((req: NextRequest & { auth: unknown }) => {
  const isAuthed = Boolean((req as { auth?: { user?: unknown } }).auth?.user);
  const pathname = req.nextUrl.pathname;

  // Protege /tablero.
  if (pathname.startsWith("/tablero") && !isAuthed) {
    const loginUrl = new URL("/login", req.nextUrl);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
});

export const config = {
  matcher: ["/tablero/:path*"],
};
