import { formatValue, prepareTableRows, type Row } from "@/lib/dashboard-data";
import type { TableBlock as TableBlockSpec } from "@/lib/schemas/dashboard";

type Props = { block: TableBlockSpec; rows: Row[] };

export function TableBlock({ block, rows }: Props) {
  const visibleRows = prepareTableRows(block, rows);
  return (
    <figure
      aria-label={block.title}
      style={{
        margin: 0,
        border: "1px solid var(--hairline)",
        background: "var(--bg-elev)",
      }}
    >
      <figcaption
        className="kicker"
        style={{
          padding: "var(--space-3) var(--space-4)",
          borderBlockEnd: "1px solid var(--hairline)",
        }}
      >
        {block.title}
      </figcaption>
      <div style={{ overflow: "auto", maxBlockSize: 320 }}>
        <table>
          <thead style={{ position: "sticky", top: 0, background: "var(--bg-elev)" }}>
            <tr>
              {block.columns.map((c) => (
                <th key={c} scope="col">
                  {c}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((r, i) => (
              <tr key={i}>
                {block.columns.map((c) => {
                  const value = r[c];
                  const isNumeric = typeof value === "number";
                  return (
                    <td
                      key={c}
                      style={{
                        fontFamily: isNumeric
                          ? "var(--font-mono)"
                          : "var(--font-sans)",
                        fontVariantNumeric: isNumeric ? "tabular-nums" : "normal",
                      }}
                    >
                      {value === null || value === undefined
                        ? "—"
                        : isNumeric
                          ? formatValue(value as number)
                          : String(value)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
