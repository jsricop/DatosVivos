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
        "py-6 text-ink-2 font-sans text-body-sm leading-[1.55]",
        isFooter ? "hairline-top" : "border-l-2 border-hairline-strong pl-4",
      ].join(" ")}
    >
      <span className="text-kicker mb-2 block">Disclaimer</span>
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
