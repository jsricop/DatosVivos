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
 * Usa Web Speech API. Locale es-CO. Si el navegador no soporta, el botón
 * queda visible pero deshabilitado con aria-label que explica el porqué.
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
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "8px 14px",
        border: `1px solid ${listening ? "var(--accent)" : "var(--hairline)"}`,
        background: listening ? "var(--bg-elev)" : "transparent",
        color: supported ? "var(--ink)" : "var(--ink-muted)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--type-caption)",
        cursor: supported ? "pointer" : "not-allowed",
      }}
    >
      <Icon name={listening ? "mic" : "mic"} size={16} aria-hidden />
      <span>{listening ? "Escuchando" : "Voz"}</span>
    </button>
  );
}
