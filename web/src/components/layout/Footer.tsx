export function Footer() {
  return (
    <footer
      className="hairline-top"
      style={{
        marginBlockStart: "var(--space-8)",
        paddingBlock: "var(--space-6)",
        color: "var(--ink-2)",
      }}
    >
      <div
        className="container-narrow"
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 24,
          justifyContent: "space-between",
          alignItems: "baseline",
        }}
      >
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-2)",
          }}
        >
          Agencia Nacional de Infraestructura — Reto #07 MinTIC 2026
        </p>
        <p
          style={{
            margin: 0,
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-muted)",
          }}
        >
          Beta · Sin trackers · El modelo corre en una máquina del Estado
        </p>
      </div>
    </footer>
  );
}
