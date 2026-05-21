import type { Metadata } from "next";

import { A11yPanel } from "@/components/A11yPanel";

export const metadata: Metadata = {
  title: "Accesibilidad",
  description:
    "Controles de accesibilidad de DatosVivos: modo de color, tamaño tipográfico, voz (STT/TTS), atajos de teclado. Cumplimiento WCAG 2.1 AA y Ley 1618 de 2013.",
  alternates: { canonical: "/accesibilidad" },
  openGraph: {
    type: "article",
    url: "/accesibilidad",
    title: "Accesibilidad · DatosVivos",
    description:
      "WCAG 2.1 AA + Ley 1618 de 2013. Modo de color, tamaño tipográfico, voz, navegación por teclado.",
  },
};

export default function AccesibilidadPage() {
  return (
    <div className="container-narrow py-12">
      <article className="measure-narrow flex flex-col gap-6">
        <header className="pb-4 hairline-bottom">
          <span className="text-kicker">Accesibilidad</span>
          <h1 className="m-0 mt-2 font-serif text-h1">
            Ajusta DatosVivos a tu lectura.
          </h1>
          <p className="m-0 mt-4 font-sans text-body-lg text-ink-2 leading-relaxed">
            DatosVivos persigue WCAG 2.1 nivel AA y cumple la Ley 1618 de 2013
            sobre accesibilidad TIC en Colombia. Tus preferencias se guardan
            en este dispositivo; no las enviamos a ningún servidor.
          </p>
        </header>

        <A11yPanel />

        <section className="pt-6 hairline-top">
          <span className="text-kicker">Compatibilidad</span>
          <ul className="mt-3 flex flex-col gap-1.5 font-sans text-body-sm text-ink-2">
            <li>Chrome y Edge — soporte óptimo de STT y TTS en es-CO.</li>
            <li>Firefox — TTS sí; STT con reconocimiento limitado.</li>
            <li>Safari — TTS sí; STT no soportado por el navegador.</li>
            <li>
              Lectores de pantalla: VoiceOver (macOS), NVDA y JAWS (Windows),
              TalkBack (Android). Si encuentras una incompatibilidad,{" "}
              <a
                href="mailto:accesibilidad@gruporq.co"
                className="border-b border-dotted border-current focus-ring"
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
