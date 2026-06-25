"use client";

import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
  size?: "md" | "lg";
  iconStart?: ReactNode;
  iconEnd?: ReactNode;
};

export function Button({
  variant = "primary",
  size = "md",
  iconStart,
  iconEnd,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const variantClass =
    variant === "primary"
      ? "border border-accent bg-accent text-bg hover:bg-accent-2 hover:border-accent-2"
      : variant === "secondary"
        ? "border border-accent text-accent bg-transparent hover:bg-bg-overlay"
        : "border border-transparent text-accent bg-transparent hover:bg-bg-overlay";
  const sizeClass =
    size === "lg" ? "px-6 py-3 text-body-lg" : "px-4 py-2 text-body";

  return (
    <button
      type="button"
      {...rest}
      className={[
        "inline-flex items-center gap-2 font-sans font-bold rounded-[var(--radius-1)] transition-colors focus-ring",
        variantClass,
        sizeClass,
        rest.disabled ? "opacity-70 cursor-not-allowed" : "cursor-pointer",
        className,
      ].join(" ")}
    >
      {iconStart}
      <span>{children}</span>
      {iconEnd}
    </button>
  );
}
