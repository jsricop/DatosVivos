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
      ? "border-2 border-accent bg-accent text-bg"
      : variant === "secondary"
        ? "border border-hairline-strong text-ink bg-transparent"
        : "border border-transparent text-ink bg-transparent";
  const sizeClass =
    size === "lg" ? "px-5 py-3 text-body-lg" : "px-[14px] py-2 text-body";

  return (
    <button
      type="button"
      {...rest}
      className={[
        "inline-flex items-center gap-2 font-sans font-semibold rounded-none transition-colors focus-ring",
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
