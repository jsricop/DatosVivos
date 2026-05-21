import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import {
  SITE_DESCRIPTION,
  SITE_LOCALE,
  SITE_NAME,
  SITE_TAGLINE,
  SITE_URL,
} from "@/lib/site";
import { ANTI_FOUC_SCALE_SCRIPT, ANTI_FOUC_SCRIPT } from "@/lib/theme";
import "../styles/globals.css";

const TITLE_DEFAULT = `${SITE_NAME} — ${SITE_TAGLINE}`;

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: TITLE_DEFAULT,
    template: `%s · ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  applicationName: SITE_NAME,
  authors: [{ name: "Agencia Nacional de Infraestructura — Oficina de Tecnología" }],
  creator: "Agencia Nacional de Infraestructura (ANI)",
  publisher: "Agencia Nacional de Infraestructura (ANI)",
  category: "government",
  keywords: [
    "datos abiertos",
    "Colombia",
    "datos.gov.co",
    "transparencia",
    "MinTIC",
    "ANI",
    "DIVIPOLA",
    "datos públicos",
    "consulta ciudadana",
    "Estado colombiano",
  ],
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-snippet": -1,
      "max-image-preview": "large",
      "max-video-preview": -1,
    },
  },
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: SITE_LOCALE,
    url: SITE_URL,
    siteName: SITE_NAME,
    title: TITLE_DEFAULT,
    description: SITE_DESCRIPTION,
    images: [
      {
        url: "/og-image.png",
        width: 1200,
        height: 630,
        alt: `${SITE_NAME} — ${SITE_TAGLINE}`,
        type: "image/png",
      },
    ],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE_DEFAULT,
    description: SITE_DESCRIPTION,
    images: ["/og-image.png"],
  },
  icons: {
    icon: [
      // SVG primero — la mayoría de navegadores modernos lo prefieren.
      { url: "/favicon.svg", type: "image/svg+xml" },
      // ICO legacy multi-resolución (16/32/48) para IE y agentes antiguos.
      { url: "/favicon.ico", sizes: "any" },
      // PNGs cuadrados para Android/PWA y agentes que esperan raster específico.
      { url: "/favicon-192.png", type: "image/png", sizes: "192x192" },
      { url: "/favicon-512.png", type: "image/png", sizes: "512x512" },
    ],
    apple: [{ url: "/apple-touch-icon.svg", type: "image/svg+xml" }],
    shortcut: [{ url: "/favicon.ico" }],
  },
  manifest: "/manifest.webmanifest",
  formatDetection: { telephone: false, email: false, address: false },
  verification: {
    // Las verifications de Google/Bing/MinTIC se rellenan via env vars
    // cuando el sitio esté en producción real bajo el dominio.
    google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION,
  },
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

const ORGANIZATION_LD = {
  "@context": "https://schema.org",
  "@type": "GovernmentOrganization",
  "@id": `${SITE_URL}#organization`,
  name: "Agencia Nacional de Infraestructura",
  alternateName: "ANI",
  url: "https://www.ani.gov.co",
  address: {
    "@type": "PostalAddress",
    addressCountry: "CO",
    addressLocality: "Bogotá D.C.",
  },
  logo: `${SITE_URL}/favicon-512.png`,
};

const WEBSITE_LD = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  "@id": `${SITE_URL}#website`,
  name: SITE_NAME,
  alternateName: "Datos Vivos",
  url: SITE_URL,
  description: SITE_DESCRIPTION,
  inLanguage: "es-CO",
  publisher: { "@id": `${SITE_URL}#organization` },
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: `${SITE_URL}/buscar?q={search_term_string}`,
    },
    "query-input": "required name=search_term_string",
  },
};

const SERVICE_LD = {
  "@context": "https://schema.org",
  "@type": "GovernmentService",
  "@id": `${SITE_URL}#service`,
  name: SITE_NAME,
  serviceType: "Consulta de datos públicos abiertos",
  description: SITE_DESCRIPTION,
  provider: { "@id": `${SITE_URL}#organization` },
  areaServed: {
    "@type": "Country",
    name: "Colombia",
  },
  audience: {
    "@type": "PeopleAudience",
    name: "Ciudadanía colombiana",
  },
  availableChannel: {
    "@type": "ServiceChannel",
    serviceUrl: SITE_URL,
    availableLanguage: "es-CO",
  },
  isAccessibleForFree: true,
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
        {/* Structured data (JSON-LD) — describe el sitio, la organización y
            el servicio para motores de búsqueda y crawlers institucionales. */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify([ORGANIZATION_LD, WEBSITE_LD, SERVICE_LD]),
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
