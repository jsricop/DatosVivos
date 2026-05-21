import Link from "next/link";

export default function NotFound() {
  return (
    <div
      className="container-narrow"
      style={{
        paddingBlock: "var(--space-8)",
        display: "flex",
        flexDirection: "column",
        gap: "var(--space-4)",
        maxInlineSize: "60ch",
      }}
    >
      <span className="kicker">404 · Página no encontrada</span>
      <h1
        style={{
          margin: 0,
          fontFamily: "var(--font-serif)",
          fontSize: "var(--type-h1)",
        }}
      >
        Esta ruta no existe.
      </h1>
      <p
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body-lg)",
          color: "var(--ink-2)",
          lineHeight: 1.6,
        }}
      >
        Es posible que el enlace que seguiste esté desactualizado o que el
        dataset que buscas haya sido removido del catálogo de datos.gov.co.
      </p>
      <Link
        href="/"
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body)",
          fontWeight: 500,
        }}
      >
        Volver al inicio →
      </Link>
    </div>
  );
}
