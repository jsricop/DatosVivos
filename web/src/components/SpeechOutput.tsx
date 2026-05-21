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

  const borderClass = speaking ? "border-accent" : "border-hairline";
  const colorClass = supported ? "text-ink-2" : "text-ink-muted cursor-not-allowed";

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
      className={[
        "inline-flex items-center gap-2 px-3 py-1.5 border bg-transparent font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] focus-ring",
        borderClass,
        colorClass,
        supported && text ? "cursor-pointer" : "",
      ].join(" ")}
    >
      <Icon name="speaker" size={14} aria-hidden />
      <span>{speaking ? "Detener" : "Leer"}</span>
    </button>
  );
}
