/**
 * Configuración de NextAuth v5 (Auth.js) — magic-link por email institucional.
 *
 * Decisión: ADR-014. Sin SSO Entra ID en Beta-2; el dominio del email
 * (`@minsalud.gov.co`, `@ani.gov.co`, etc.) identifica la entidad. Si la
 * ANI activa SSO real más adelante, se cambia el provider sin tocar UI.
 */

import NextAuth, { type DefaultSession } from "next-auth";
import Nodemailer from "next-auth/providers/nodemailer";

declare module "next-auth" {
  interface Session extends DefaultSession {
    user: {
      entityId: number | null;
      entityName: string | null;
      entityAbbrev: string | null;
    } & DefaultSession["user"];
  }
}

const ALLOWED_DOMAINS = (process.env.AUTH_ALLOWED_DOMAINS ?? ".gov.co")
  .split(",")
  .map((d) => d.trim().toLowerCase())
  .filter(Boolean);

function isAllowedEmail(email: string | null | undefined): boolean {
  if (!email) return false;
  const lower = email.toLowerCase();
  return ALLOWED_DOMAINS.some((d) =>
    d.startsWith(".") ? lower.endsWith(d) : lower.endsWith(`@${d}`),
  );
}

async function resolveEntity(email: string): Promise<{
  entityId: number | null;
  entityName: string | null;
  entityAbbrev: string | null;
}> {
  // Lookup en Postgres. Si DATABASE_URL no está o falla, devuelve null en todos
  // los campos — la sesión se crea pero el dashboard mostrará "Sin entidad".
  const url = process.env.DATABASE_URL;
  if (!url) {
    return { entityId: null, entityName: null, entityAbbrev: null };
  }
  try {
    const domain = "@" + email.split("@")[1]!.toLowerCase();
    const { Client } = await import("pg");
    const client = new Client({ connectionString: url });
    await client.connect();
    try {
      const result = await client.query<{
        entity_id: number;
        name: string;
        abbrev: string | null;
      }>(
        "SELECT entity_id, name, abbrev FROM entities WHERE LOWER(domain_email) = $1 LIMIT 1",
        [domain],
      );
      const row = result.rows[0];
      if (!row) {
        return { entityId: null, entityName: null, entityAbbrev: null };
      }
      return {
        entityId: row.entity_id,
        entityName: row.name,
        entityAbbrev: row.abbrev,
      };
    } finally {
      await client.end();
    }
  } catch {
    return { entityId: null, entityName: null, entityAbbrev: null };
  }
}

async function logAuthEvent(
  email: string,
  entityId: number | null,
  eventType: string,
  detail: Record<string, unknown> = {},
): Promise<void> {
  const url = process.env.DATABASE_URL;
  if (!url) return;
  try {
    const { Client } = await import("pg");
    const client = new Client({ connectionString: url });
    await client.connect();
    try {
      await client.query(
        `INSERT INTO auth_events (email, entity_id, event_type, detail)
         VALUES ($1, $2, $3, $4::jsonb)`,
        [email, entityId, eventType, JSON.stringify(detail)],
      );
    } finally {
      await client.end();
    }
  } catch {
    /* best-effort */
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  session: { strategy: "jwt", maxAge: 60 * 60 * 24 * 30 }, // 30 días
  pages: {
    signIn: "/login",
    verifyRequest: "/login?status=link-enviado",
    error: "/login?status=error",
  },
  providers: process.env.SMTP_URL
    ? [
        Nodemailer({
          server: process.env.SMTP_URL,
          from: process.env.SMTP_FROM ?? "DatosVivos <accesos@datosvivos.co>",
          maxAge: 60 * 30, // magic link válido 30 minutos
        }),
      ]
    : [],
  trustHost: true,
  callbacks: {
    async signIn({ user }) {
      const allowed = isAllowedEmail(user.email);
      if (!allowed) {
        await logAuthEvent(user.email ?? "", null, "login_rejected", {
          reason: "domain_not_allowed",
        });
        return false;
      }
      return true;
    },
    async jwt({ token, user, trigger }) {
      // En el primer sign-in `user` está poblado; persistimos la entidad
      // resuelta en el token JWT para no consultar Postgres en cada request.
      if (user?.email && (trigger === "signIn" || !token.entityId)) {
        const entity = await resolveEntity(user.email);
        token.entityId = entity.entityId;
        token.entityName = entity.entityName;
        token.entityAbbrev = entity.entityAbbrev;
        await logAuthEvent(user.email, entity.entityId, "login_success", {});
      }
      return token;
    },
    async session({ session, token }) {
      session.user.entityId = (token.entityId as number | null) ?? null;
      session.user.entityName = (token.entityName as string | null) ?? null;
      session.user.entityAbbrev = (token.entityAbbrev as string | null) ?? null;
      return session;
    },
  },
  events: {
    async signOut(payload) {
      const token = "token" in payload ? payload.token : null;
      const email = token && typeof token.email === "string" ? token.email : null;
      const entityId =
        token && typeof token.entityId === "number" ? token.entityId : null;
      if (email) {
        await logAuthEvent(email, entityId, "logout", {});
      }
    },
  },
});
