type DisclaimerBetaProps = {
  variant?: "inline" | "footer";
};

/**
 * DisclaimerBeta (BRAND.md §8.10 + §1.3) — texto fijo, no editable.
 *
 * Usa las tres anclas léxicas declaradas en BRAND.md §1.3:
 *   "Datos verificados" · "Fuentes consultadas" · "No encontré datasets relevantes".
 */
export function DisclaimerBeta({ variant = "inline" }: DisclaimerBetaProps) {
  const isFooter = variant === "footer";
  return (
    <aside
      className={[
        "text-ink-2 font-sans text-body-sm leading-[1.55]",
        isFooter
          ? "mt-6 pt-6 hairline-top"
          : "rounded-[var(--radius-2)] border border-hairline border-l-4 border-l-accent bg-bg-elev p-4",
      ].join(" ")}
    >
      <span className="mb-2 inline-flex items-center gap-2">
        <span className="rounded-[var(--radius-1)] bg-accent px-2 py-0.5 font-sans text-[length:var(--type-kicker)] font-bold uppercase tracking-wide text-bg">
          Beta
        </span>
        <span className="text-kicker">Cómo leer esta respuesta</span>
      </span>
      <p className="m-0">
        Esta es la versión Beta-1. Las cifras del bloque{" "}
        <strong className="text-ink">Datos verificados</strong> salen
        directamente de los datasets citados en{" "}
        <strong className="text-ink">Fuentes consultadas</strong> — no se
        inventan. Si DatosVivos no puede responder tu pregunta, te lo dice
        claramente con el mensaje{" "}
        <strong className="text-ink">«No encontré datasets relevantes»</strong>:
        nunca improvisa una respuesta. Abre la fuente original para verificar
        cualquier dato.
      </p>
    </aside>
  );
}
