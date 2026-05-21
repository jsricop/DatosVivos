"use client";

import { useEffect, useState } from "react";

import { Icon } from "@/components/Icon";

type SpeechOutputProps = {
  text: string;
  lang?: string;
};

export function SpeechOutput({ text, lang = "es-CO" }: SpeechOutputProps) {
  const [supported, setSupported] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  useEffect(() => {
    setSupported(typeof window !== "undefined" && "speechSynthesis" in window);
  }, []);

  function speak() {
    if (!supported || !text) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang;
    utter.rate = 1;
    utter.onend = () => setSpeaking(false);
    utter.onerror = () => setSpeaking(false);
    window.speechSynthesis.speak(utter);
    setSpeaking(true);
  }

  function stop() {
    window.speechSynthesis.cancel();
    setSpeaking(false);
  }

  return (
    <button
      type="button"
      onClick={() => (speaking ? stop() : speak())}
      disabled={!supported || !text}
      aria-pressed={speaking}
      aria-label={
        !supported
          ? "Lectura por voz no disponible en este navegador"
          : speaking
            ? "Detener lectura"
            : "Leer en voz alta"
      }
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: "6px 12px",
        border: `1px solid ${speaking ? "var(--accent)" : "var(--hairline)"}`,
        background: "transparent",
        color: supported ? "var(--ink-2)" : "var(--ink-muted)",
        fontFamily: "var(--font-mono)",
        fontSize: "var(--type-kicker)",
        textTransform: "uppercase",
        letterSpacing: "0.08em",
        cursor: supported && text ? "pointer" : "not-allowed",
      }}
    >
      <Icon name={speaking ? "speaker" : "speaker"} size={14} aria-hidden />
      <span>{speaking ? "Detener" : "Leer"}</span>
    </button>
  );
}
