type Props = { items: string[] };

export function Caveats({ items }: Props) {
  if (items.length === 0) return null;
  return (
    <aside
      role="note"
      aria-label="Advertencias"
      style={{
        borderInlineStart: "2px solid var(--accent-2)",
        paddingInlineStart: "var(--space-4)",
        paddingBlock: "var(--space-3)",
        marginBlockStart: "var(--space-4)",
        color: "var(--ink-2)",
      }}
    >
      <span className="kicker" style={{ display: "block", marginBlockEnd: 8 }}>
        Advertencias
      </span>
      <ul style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        {items.map((item, i) => (
          <li
            key={i}
            style={{
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
              lineHeight: 1.55,
            }}
          >
            {item}
          </li>
        ))}
      </ul>
    </aside>
  );
}
