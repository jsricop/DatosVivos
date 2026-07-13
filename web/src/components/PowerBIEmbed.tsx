"use client";

import { useEffect, useRef, useState } from "react";

/**
 * Embed de Power BI «Publicar en la web» que SIEMPRE llena el marco.
 *
 * El truco de la proporción (aspect-ratio) no bastó: el reporte se
 * renderiza a su tamaño NATIVO de página y aparecía al 100% con scroll
 * horizontal (2026-07-13). Aquí el iframe se renderiza al tamaño nativo
 * del reporte y se ESCALA con transform al ancho real del contenedor —
 * como hace un visor de PDF. Sin scroll interno, sin zoom manual, a
 * cualquier resolución.
 *
 * El tamaño nativo llega por props (env PBI_REPORT_WIDTH/HEIGHT en el
 * server component): si el .pbix cambia de lienzo, se ajusta sin rebuild.
 */
export function PowerBIEmbed({
  src,
  title,
  nativeWidth,
  nativeHeight,
}: {
  src: string;
  title: string;
  /** Ancho del lienzo del reporte en px (default 1280). */
  nativeWidth: number;
  /** Alto del lienzo + barra inferior de PBI en px (default 720 + 56). */
  nativeHeight: number;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;
    const measure = () => {
      const w = host.clientWidth;
      if (w > 0) setScale(w / nativeWidth);
    };
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(host);
    return () => ro.disconnect();
  }, [nativeWidth]);

  return (
    <div
      ref={hostRef}
      className="w-full overflow-hidden"
      style={{ height: Math.round(nativeHeight * scale) }}
    >
      <iframe
        src={src}
        title={title}
        allowFullScreen
        loading="lazy"
        referrerPolicy="strict-origin-when-cross-origin"
        className="block border-0 bg-bg-elev"
        style={{
          width: nativeWidth,
          height: nativeHeight,
          transform: `scale(${scale})`,
          transformOrigin: "top left",
        }}
      />
    </div>
  );
}
