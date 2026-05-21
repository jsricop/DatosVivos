type DisclaimerBetaProps = {
  variant?: "inline" | "footer";
};

const TEXT = (
  <>
    DatosVivos está en versión Beta-1. Cada cifra que aparece arriba está
    calculada con <code className="mono">pandas</code> sobre los datos reales
    del dataset citado. Si una afirmación parece imprecisa, abre el dataset
    original y verifícalo.
  </>
);

/**
 * DisclaimerBeta (BRAND.md §8.10) — texto fijo, no editable.
 */
export function DisclaimerBeta({ variant = "inline" }: DisclaimerBetaProps) {
  return (
    <aside
      className={variant === "footer" ? "hairline-top" : ""}
      style={{
        paddingBlock: "var(--space-5)",
        color: "var(--ink-2)",
        fontFamily: "var(--font-sans)",
        fontSize: "var(--type-body-sm)",
        lineHeight: 1.55,
        ...(variant === "inline"
          ? {
              borderInlineStart: "2px solid var(--hairline-strong)",
              paddingInlineStart: "var(--space-4)",
            }
          : {}),
      }}
    >
      <span className="kicker" style={{ display: "block", marginBottom: 8 }}>
        Disclaimer
      </span>
      {TEXT}
    </aside>
  );
}
