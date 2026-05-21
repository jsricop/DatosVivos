import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { ANTI_FOUC_SCALE_SCRIPT, ANTI_FOUC_SCRIPT } from "@/lib/theme";
import "../styles/globals.css";

export const metadata: Metadata = {
  title: {
    default: "Datos|Vivos — Datos del Estado, en tus palabras.",
    template: "%s · Datos|Vivos",
  },
  applicationName: "DatosVivos",
  authors: [{ name: "Agencia Nacional de Infraestructura — Oficina de Tecnología" }],
  generator: "Next.js",
  keywords: [
    "datos abiertos",
    "Colombia",
    "datos.gov.co",
    "agente IA",
    "MinTIC",
    "ANI",
    "DIVIPOLA",
    "soberanía de datos",
  ],
  robots: { index: true, follow: true },
  icons: {
    icon: [
      { url: "/favicon.svg", type: "image/svg+xml" },
      { url: "/icon.svg", type: "image/svg+xml", sizes: "any" },
    ],
    apple: [{ url: "/apple-touch-icon.svg", type: "image/svg+xml" }],
    shortcut: [{ url: "/favicon.svg" }],
  },
  description:
    "Agente civil de datos abiertos del Estado colombiano. Pregunta en lenguaje natural sobre cualquier dato público y recibe la respuesta con la fuente original a un click.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#F3EFE3" },
    { media: "(prefers-color-scheme: dark)", color: "#0E0C08" },
  ],
  width: "device-width",
  initialScale: 1,
  minimumScale: 1,
  maximumScale: 5,
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="es-CO" data-theme="light" suppressHydrationWarning>
      <head>
        {/* Anti-FOUC: aplica modo de color y escala tipográfica antes del hidrato.
            Lee localStorage["datosvivos:theme"] y "datosvivos:font-scale".
            Patrón inspirado en GOV.UK Design System. */}
        <script
          dangerouslySetInnerHTML={{
            __html: ANTI_FOUC_SCRIPT + ANTI_FOUC_SCALE_SCRIPT,
          }}
        />
      </head>
      <body>
        <a className="skip-link" href="#contenido">
          Saltar al contenido principal
        </a>
        <Header />
        <main id="contenido" tabIndex={-1}>
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
