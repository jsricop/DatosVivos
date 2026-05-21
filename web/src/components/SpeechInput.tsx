"use client";

import { useEffect, useRef, useState } from "react";

import { Icon } from "@/components/Icon";

type SpeechInputProps = {
  onTranscript: (text: string) => void;
  lang?: string;
};

type SpeechRecognitionLike = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: { results: ArrayLike<{ 0: { transcript: string } }> }) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
};

declare global {
  interface Window {
    SpeechRecognition?: { new (): SpeechRecognitionLike };
    webkitSpeechRecognition?: { new (): SpeechRecognitionLike };
  }
}

/**
 * SpeechInput (BRAND.md §8.12) — botón STT.
 *
 * Usa Web Speech API. Locale es-CO por defecto. Si el navegador no soporta,
 * el botón queda visible pero deshabilitado con aria-label explicativo.
 */
export function SpeechInput({ onTranscript, lang = "es-CO" }: SpeechInputProps) {
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef<SpeechRecognitionLike | null>(null);

  useEffect(() => {
    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    setSupported(Boolean(SR));
  }, []);

  function start() {
    const SR = window.SpeechRecognition ?? window.webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.lang = lang;
    rec.interimResults = false;
    rec.continuous = false;
    rec.onresult = (event) => {
      const transcript = event.results?.[0]?.[0]?.transcript ?? "";
      if (transcript) onTranscript(transcript);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    recognitionRef.current = rec;
    setListening(true);
    rec.start();
  }

  function stop() {
    recognitionRef.current?.stop();
    setListening(false);
  }

  const borderClass = listening ? "border-accent bg-bg-elev" : "border-hairline bg-transparent";
  const colorClass = supported ? "text-ink cursor-pointer" : "text-ink-muted cursor-not-allowed";

  return (
    <button
      type="button"
      onClick={() => (listening ? stop() : start())}
      disabled={!supported}
      aria-pressed={listening}
      aria-label={
        !supported
          ? "Entrada por voz no disponible en este navegador"
          : listening
            ? "Detener entrada por voz"
            : "Iniciar entrada por voz"
      }
      className={[
        "inline-flex items-center gap-2 px-[14px] py-2 border font-mono text-caption focus-ring",
        borderClass,
        colorClass,
      ].join(" ")}
    >
      <Icon name="mic" size={16} aria-hidden />
      <span>{listening ? "Escuchando" : "Voz"}</span>
    </button>
  );
}
