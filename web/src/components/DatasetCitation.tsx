import { Icon } from "@/components/Icon";
import type { DatasetCitation as Citation } from "@/lib/types";

export function DatasetCitation({ citation }: { citation: Citation }) {
  return (
    <li
      id={`cita-${citation.index}`}
      className="grid grid-cols-[auto_1fr] gap-3 py-4 hairline-top"
    >
      <span
        className="font-mono text-body font-medium text-accent"
        aria-hidden
      >
        [{citation.index}]
      </span>
      <div>
        <span className="text-kicker">{citation.entity ?? "Entidad no declarada"}</span>
        <h4 className="font-serif text-h4 font-semibold m-0 mt-1 mb-2">
          {citation.name}
        </h4>
        <p className="font-mono text-caption text-ink-2 m-0 mb-2">
          id: <span className="text-ink">{citation.id}</span>
        </p>
        <div className="flex flex-wrap gap-4 items-center">
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 font-sans text-body-sm focus-ring"
          >
            <span>ver dataset</span>
            <Icon name="external-link" size={14} aria-hidden />
          </a>
          <a
            href={citation.api_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 font-sans text-body-sm focus-ring"
          >
            <span>JSON SODA</span>
            <Icon name="external-link" size={14} aria-hidden />
          </a>
        </div>
      </div>
    </li>
  );
}
