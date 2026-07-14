import { Icon } from "@/components/Icon";
import type { DatasetCitation as Citation } from "@/lib/types";

export function DatasetCitation({ citation }: { citation: Citation }) {
  return (
    <li
      id={`cita-${citation.index}`}
      className="surface-card mb-3 grid grid-cols-[auto_1fr] gap-3 p-4"
    >
      <span
        className="inline-flex h-6 min-w-6 items-center justify-center rounded-[var(--radius-1)] bg-accent px-1.5 font-mono text-caption font-bold text-bg"
        aria-hidden
      >
        {citation.index}
      </span>
      <div>
        <span className="text-kicker">{citation.entity ?? "Entidad no declarada"}</span>
        <h4 className="font-sans text-h4 font-bold m-0 mt-1 mb-2">
          {citation.name}
        </h4>
        <p className="font-mono text-caption text-ink-2 m-0 mb-3">
          id: <span className="text-ink">{citation.id}</span>
        </p>
        <div className="flex flex-wrap gap-2 items-center">
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-1)] border border-accent px-3 py-1 font-sans text-body-sm font-semibold text-accent no-underline hover:bg-bg-overlay focus-ring"
          >
            <span>Ver dataset</span>
            <Icon name="external-link" size={14} aria-hidden />
          </a>
          <a
            href={citation.api_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-[var(--radius-1)] border border-hairline px-3 py-1 font-sans text-body-sm text-ink-2 no-underline hover:border-accent focus-ring"
          >
            <span>JSON SODA</span>
            <Icon name="external-link" size={14} aria-hidden />
          </a>
        </div>
      </div>
    </li>
  );
}
