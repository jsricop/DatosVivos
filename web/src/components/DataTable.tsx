"use client";

import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";

import type { Row } from "@/lib/types";

type DataTableProps = {
  columns: string[];
  rows: Row[];
  caption?: string;
  pageSize?: number;
};

/**
 * DataTable (BRAND.md §8.7) — TanStack headless.
 *
 * Tipografía Plex Mono tabular-nums en celdas numéricas. Sin zebra striping;
 * regletas hairline entre filas. Header sticky.
 */
export function DataTable({
  columns,
  rows,
  caption,
  pageSize = 25,
}: DataTableProps) {
  const tableColumns = useMemo(
    () =>
      columns.map((col) => ({
        accessorKey: col,
        header: col,
        cell: ({ getValue }: { getValue: () => unknown }) => {
          const v = getValue();
          if (v === null || v === undefined) return "—";
          return String(v);
        },
      })),
    [columns],
  );

  const table = useReactTable({
    data: rows,
    columns: tableColumns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  if (rows.length === 0) {
    return (
      <p
        style={{
          fontFamily: "var(--font-sans)",
          fontSize: "var(--type-body-sm)",
          color: "var(--ink-muted)",
          padding: "var(--space-4)",
        }}
      >
        La consulta no devolvió filas.
      </p>
    );
  }

  return (
    <div
      role="region"
      aria-label="Tabla de datos crudos"
      style={{
        border: "1px solid var(--hairline)",
        overflow: "auto",
        maxBlockSize: "60vh",
      }}
    >
      <table style={{ minWidth: "100%" }}>
        {caption ? (
          <caption
            style={{
              padding: "var(--space-3) var(--space-4)",
              fontFamily: "var(--font-mono)",
              fontSize: "var(--type-caption)",
              color: "var(--ink-2)",
              textAlign: "start",
              captionSide: "top",
            }}
          >
            {caption}
          </caption>
        ) : null}
        <thead style={{ position: "sticky", top: 0, background: "var(--bg-elev)" }}>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => (
                <th key={header.id} scope="col">
                  {flexRender(header.column.columnDef.header, header.getContext())}
                </th>
              ))}
            </tr>
          ))}
        </thead>
        <tbody>
          {table.getRowModel().rows.map((row) => (
            <tr key={row.id}>
              {row.getVisibleCells().map((cell) => {
                const value = cell.getValue();
                const isNumeric =
                  typeof value === "number" ||
                  (typeof value === "string" && /^-?\d/.test(value));
                return (
                  <td
                    key={cell.id}
                    style={{
                      fontFamily: isNumeric
                        ? "var(--font-mono)"
                        : "var(--font-sans)",
                      fontVariantNumeric: isNumeric ? "tabular-nums" : "normal",
                    }}
                  >
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {table.getPageCount() > 1 ? (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "var(--space-3) var(--space-4)",
            borderBlockStart: "1px solid var(--hairline)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--type-caption)",
          }}
        >
          <span>
            Página {table.getState().pagination.pageIndex + 1} de{" "}
            {table.getPageCount()}
          </span>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              type="button"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              style={{
                border: "1px solid var(--hairline)",
                padding: "4px 10px",
              }}
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              style={{
                border: "1px solid var(--hairline)",
                padding: "4px 10px",
              }}
            >
              Siguiente
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
