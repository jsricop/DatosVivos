import { Icon } from "@/components/Icon";
import type { DatasetCitation as Citation } from "@/lib/types";

export function DatasetCitation({ citation }: { citation: Citation }) {
  return (
    <li
      id={`cita-${citation.index}`}
      style={{
        display: "grid",
        gridTemplateColumns: "auto 1fr",
        gap: 12,
        paddingBlock: "var(--space-4)",
        borderBlockStart: "1px solid var(--hairline)",
      }}
    >
      <span
        style={{
          fontFamily: "var(--font-mono)",
          fontSize: "var(--type-body)",
          fontWeight: 500,
          color: "var(--accent)",
        }}
        aria-hidden
      >
        [{citation.index}]
      </span>
      <div>
        <span className="kicker">{citation.entity ?? "Entidad no declarada"}</span>
        <h4
          style={{
            margin: "4px 0 8px 0",
            fontFamily: "var(--font-serif)",
            fontSize: "var(--type-h4)",
            fontWeight: 600,
          }}
        >
          {citation.name}
        </h4>
        <p
          style={{
            margin: "0 0 8px 0",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
            color: "var(--ink-2)",
          }}
        >
          id: <span style={{ color: "var(--ink)" }}>{citation.id}</span>
        </p>
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 16,
            alignItems: "center",
          }}
        >
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontFamily: "var(--font-sans)",
              fontSize: "var(--type-body-sm)",
            }}
          >
            <span>ver dataset</span>
            <Icon name="external-link" size={14} aria-hidden />
          </a>
          <a
            href={citation.api_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-2)",
            }}
          >
            <span>JSON SODA</span>
            <Icon name="external-link" size={12} aria-hidden />
          </a>
        </div>
      </div>
    </li>
  );
}
