"use client";

import { useEffect } from "react";

type GlobalErrorProps = {
  error: Error & { digest?: string };
  reset: () => void;
};

/**
 * Error boundary global del App Router (Next.js 15).
 *
 * Captura excepciones cliente no manejadas. Muestra una página honesta y
 * deja la posibilidad de reintentar — no la app en blanco. PLAN_DASHBOARD
 * §11.8 (auditabilidad) sugiere mostrar el mensaje real del error.
 */
export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    // Reporta a consola por ahora. En producción se podría enviar a /api/v1/telemetry.
    // eslint-disable-next-line no-console
    console.error("DatosVivos error boundary:", error);
  }, [error]);

  return (
    <div className="container-narrow py-12 max-w-[60ch] flex flex-col gap-4">
      <span className="text-kicker">Error inesperado</span>
      <h1 className="m-0 font-sans text-h1">
        Algo salió mal procesando tu consulta.
      </h1>
      <p className="font-sans text-body-lg text-ink-2 leading-relaxed">
        El error se registró en consola del servidor para que el equipo lo
        revise. Si quieres intentar de nuevo, usa el botón. Si el problema
        persiste, regresa al inicio y reformula la pregunta.
      </p>
      <pre className="font-mono text-caption text-ink-2 surface-elev p-3 overflow-auto whitespace-pre-wrap">
        {error.message || "Error sin mensaje"}
        {error.digest ? `\n\nDigest: ${error.digest}` : ""}
      </pre>
      <div className="flex gap-3 mt-2">
        <button
          type="button"
          onClick={reset}
          className="inline-flex items-center gap-2 rounded-[var(--radius-1)] border border-accent bg-accent text-bg px-6 py-3 font-sans text-body-lg font-bold hover:bg-accent-2 transition-colors focus-ring"
        >
          Reintentar
        </button>
        <a
          href="/"
          className="inline-flex items-center gap-2 rounded-[var(--radius-1)] border border-accent px-6 py-3 font-sans text-body-lg text-accent no-underline hover:bg-bg-overlay focus-ring"
        >
          Volver al inicio
        </a>
      </div>
    </div>
  );
}
