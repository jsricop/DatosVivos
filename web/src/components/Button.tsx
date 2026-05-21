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
  children,
  style,
  ...rest
}: ButtonProps) {
  const isPrimary = variant === "primary";
  const isSecondary = variant === "secondary";
  return (
    <button
      type="button"
      {...rest}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 8,
        padding: size === "lg" ? "12px 20px" : "8px 14px",
        borderRadius: "var(--radius-0)",
        border:
          isPrimary
            ? "2px solid var(--accent)"
            : isSecondary
              ? "1px solid var(--hairline-strong)"
              : "1px solid transparent",
        background: isPrimary ? "var(--accent)" : "transparent",
        color: isPrimary ? "var(--bg)" : "var(--ink)",
        fontFamily: "var(--font-sans)",
        fontSize: size === "lg" ? "var(--type-body-lg)" : "var(--type-body)",
        fontWeight: 600,
        cursor: rest.disabled ? "not-allowed" : "pointer",
        opacity: rest.disabled ? 0.7 : 1,
        transition: "background var(--duration-fast) var(--easing-standard), border-color var(--duration-fast) var(--easing-standard)",
        ...style,
      }}
    >
      {iconStart}
      <span>{children}</span>
      {iconEnd}
    </button>
  );
}
