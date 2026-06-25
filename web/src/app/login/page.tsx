import type { Metadata } from "next";

import { Icon } from "@/components/Icon";
import { signIn } from "@/lib/auth";

export const metadata: Metadata = {
  title: "Acceso institucional",
  description:
    "Acceso al tablero ejecutivo de DatosVivos. Recibe un enlace seguro en tu correo institucional.",
  robots: { index: false, follow: false },
};

type SearchParams = Promise<{ callbackUrl?: string; status?: string }>;

export default async function LoginPage({
  searchParams,
}: {
  searchParams: SearchParams;
}) {
  const { callbackUrl, status } = await searchParams;

  async function requestLink(formData: FormData) {
    "use server";
    const email = String(formData.get("email") ?? "").trim();
    if (!email) return;
    await signIn("nodemailer", {
      email,
      redirectTo: callbackUrl || "/tablero",
    });
  }

  const isLinkSent = status === "link-enviado";
  const isError = status === "error";

  return (
    <div className="container-narrow py-16">
      <article className="measure-narrow flex flex-col gap-6">
        <header className="pb-4 hairline-bottom">
          <span className="text-kicker">Acceso institucional</span>
          <h1 className="m-0 mt-2 font-sans text-h1">
            Tablero ejecutivo por entidad
          </h1>
          <p className="m-0 mt-4 font-sans text-body-lg text-ink-2 leading-relaxed">
            DatosVivos identifica tu entidad por el dominio de tu correo
            institucional (<code className="font-mono">.gov.co</code>). Al
            ingresar recibirás un enlace seguro en tu bandeja — sin
            contraseñas, sin registros.
          </p>
        </header>

        {isLinkSent ? (
          <div
            role="status"
            className="surface-elev p-5 flex flex-col gap-2"
          >
            <span className="text-kicker text-accent">Enlace enviado</span>
            <p className="m-0 font-sans text-body">
              Revisa tu bandeja institucional. El enlace expira en 30 minutos.
              Si no lo recibes, verifica que tu dominio termine en{" "}
              <code className="font-mono">.gov.co</code>.
            </p>
          </div>
        ) : null}

        {isError ? (
          <div
            role="alert"
            className="surface-elev p-5 flex flex-col gap-2 border-danger"
          >
            <span className="text-kicker text-danger">Error</span>
            <p className="m-0 font-sans text-body">
              No pudimos enviar el enlace. Verifica que tu correo sea
              institucional y vuelve a intentarlo.
            </p>
          </div>
        ) : null}

        <form
          action={requestLink}
          className="flex flex-col gap-4"
          aria-label="Solicitar enlace de acceso"
        >
          <label className="flex flex-col gap-2">
            <span className="text-kicker">Correo institucional</span>
            <input
              type="email"
              name="email"
              required
              placeholder="tu.nombre@minsalud.gov.co"
              autoComplete="email"
              className="datosvivos-search-input rounded-[var(--radius-2)] border border-hairline bg-bg-elev px-4 py-3 font-sans text-body-lg text-ink focus-ring"
            />
          </label>
          <button
            type="submit"
            className="self-start inline-flex items-center gap-2 rounded-[var(--radius-1)] border border-accent bg-accent text-bg px-6 py-3 font-sans text-body-lg font-bold hover:bg-accent-2 transition-colors focus-ring"
          >
            <Icon name="enter" size={18} aria-hidden />
            Enviarme el enlace
          </button>
        </form>

        <section className="pt-6 hairline-top">
          <span className="text-kicker">Privacidad</span>
          <p className="m-0 mt-2 font-sans text-body-sm text-ink-2 leading-relaxed">
            Tu correo se usa solo para identificar a tu entidad y abrirte el
            tablero correspondiente. No lo compartimos con terceros ni lo usamos
            para marketing. Los accesos se registran para auditoría
            institucional (fecha, dominio, IP).
          </p>
        </section>
      </article>
    </div>
  );
}
