import { formatValue, prepareTableRows, type Row } from "@/lib/dashboard-data";
import type { TableBlock as TableBlockSpec } from "@/lib/schemas/dashboard";

type Props = { block: TableBlockSpec; rows: Row[] };

export function TableBlock({ block, rows }: Props) {
  const visibleRows = prepareTableRows(block, rows);
  return (
    <figure aria-label={block.title} className="surface-elev m-0">
      <figcaption className="text-kicker px-4 py-3 hairline-bottom">
        {block.title}
      </figcaption>
      <div className="overflow-auto max-h-[320px]">
        <table>
          <thead className="sticky top-0 bg-bg-elev">
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
                      className={
                        isNumeric
                          ? "font-mono [font-variant-numeric:tabular-nums]"
                          : "font-sans"
                      }
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
