import Link from "next/link";

export default function NotFound() {
  return (
    <div className="container-narrow py-16 flex flex-col gap-4 max-w-[60ch]">
      <span className="text-kicker">404 · Página no encontrada</span>
      <h1 className="m-0 font-sans text-h1">Esta ruta no existe.</h1>
      <p className="font-sans text-body-lg text-ink-2 leading-relaxed">
        Es posible que el enlace que seguiste esté desactualizado o que el
        dataset que buscas haya sido removido del catálogo de datos.gov.co.
      </p>
      <Link href="/" className="font-sans text-body font-medium focus-ring">
        Volver al inicio →
      </Link>
    </div>
  );
}
