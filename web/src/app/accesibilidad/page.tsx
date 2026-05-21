import type { Metadata } from "next";

import { A11yPanel } from "@/components/A11yPanel";

export const metadata: Metadata = {
  title: "Accesibilidad",
  description:
    "Controles de accesibilidad de DatosVivos: modo de color, tamaño tipográfico, voz, atajos de teclado. Cumplimiento WCAG 2.1 AA y Ley 1618 de 2013.",
};

export default function AccesibilidadPage() {
  return (
    <div
      className="container-narrow"
      style={{ paddingBlock: "var(--space-7)" }}
    >
      <article
        className="measure-narrow"
        style={{ display: "flex", flexDirection: "column", gap: "var(--space-5)" }}
      >
        <header
          style={{
            paddingBlockEnd: "var(--space-4)",
            borderBlockEnd: "1px solid var(--hairline)",
          }}
        >
          <span className="kicker">Accesibilidad</span>
          <h1
            style={{
              margin: "8px 0 0 0",
              fontFamily: "var(--font-serif)",
              fontSize: "var(--type-h1)",
            }}
          >
            Ajusta DatosVivos a tu lectura.
          </h1>
          <p
            style={{
              margin: "16px 0 0 0",
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-lg)",
              color: "var(--ink-2)",
              lineHeight: 1.6,
            }}
          >
            DatosVivos persigue WCAG 2.1 nivel AA y cumple la Ley 1618 de 2013
            sobre accesibilidad TIC en Colombia. Tus preferencias se guardan en
            este dispositivo; no las enviamos a ningún servidor.
          </p>
        </header>

        <A11yPanel />

        <section
          style={{
            paddingBlockStart: "var(--space-5)",
            borderBlockStart: "1px solid var(--hairline)",
          }}
        >
          <span className="kicker">Compatibilidad</span>
          <ul
            style={{
              marginBlockStart: 12,
              display: "flex",
              flexDirection: "column",
              gap: 6,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              color: "var(--ink-2)",
            }}
          >
            <li>Chrome y Edge — soporte óptimo de STT y TTS en es-CO.</li>
            <li>Firefox — TTS sí; STT con reconocimiento limitado.</li>
            <li>Safari — TTS sí; STT no soportado por el navegador.</li>
            <li>
              Lectores de pantalla: VoiceOver (macOS), NVDA y JAWS (Windows),
              TalkBack (Android). Si encuentras una incompatibilidad,{" "}
              <a
                href="mailto:accesibilidad@gruporq.co"
                style={{ borderBottom: "1px dotted currentColor" }}
              >
                escríbenos
              </a>
              .
            </li>
          </ul>
        </section>
      </article>
    </div>
  );
}
