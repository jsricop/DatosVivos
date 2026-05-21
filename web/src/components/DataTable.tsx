"use client";

import {
  flexRender,
  getCoreRowModel,
  getPaginationRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { useCallback, useMemo } from "react";

import { Icon } from "@/components/Icon";
import type { Row } from "@/lib/types";

type DataTableProps = {
  columns: string[];
  rows: Row[];
  caption?: string;
  pageSize?: number;
  /** Si está presente, agrega botón "Descargar CSV" (B.1 — auditabilidad MinTIC). */
  downloadFilename?: string;
};

/**
 * DataTable (BRAND.md §8.7) — TanStack headless.
 *
 * Tipografía Plex Mono tabular-nums en celdas numéricas. Regletas hairline,
 * sin zebra striping. Header sticky. Botón CSV cumple PLAN_DASHBOARD §11.8.
 */
export function DataTable({
  columns,
  rows,
  caption,
  pageSize = 25,
  downloadFilename = "rows.csv",
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

  const downloadCsv = useCallback(() => {
    const escape = (v: unknown) => {
      const s = v === null || v === undefined ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    const csv = [
      columns.join(","),
      ...rows.map((r) => columns.map((c) => escape(r[c])).join(",")),
    ].join("\n");
    // BOM para que Excel/Numbers detecten UTF-8 con tildes/eñes correctamente.
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [columns, rows, downloadFilename]);

  if (rows.length === 0) {
    return (
      <p className="font-sans text-body-sm text-ink-muted p-4">
        La consulta no devolvió filas.
      </p>
    );
  }

  return (
    <div
      role="region"
      aria-label="Tabla de datos crudos"
      className="border border-hairline overflow-auto max-h-[60vh]"
    >
      <div className="flex justify-between items-center px-4 py-3 hairline-bottom bg-bg-elev sticky top-0 z-10">
        <span className="text-kicker">
          {rows.length.toLocaleString("es-CO")} filas
        </span>
        <button
          type="button"
          onClick={downloadCsv}
          className="inline-flex items-center gap-2 border border-hairline-strong px-3 py-1.5 font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] text-ink hover:bg-bg focus-ring"
          aria-label="Descargar CSV con todas las filas"
        >
          <Icon name="download" size={14} aria-hidden />
          <span>Descargar CSV</span>
        </button>
      </div>
      <table className="min-w-full">
        {caption ? (
          <caption className="px-4 py-3 font-mono text-caption text-ink-2 text-start caption-top">
            {caption}
          </caption>
        ) : null}
        <thead>
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
                    className={isNumeric ? "font-mono [font-variant-numeric:tabular-nums]" : "font-sans"}
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
        <div className="flex justify-between items-center px-4 py-3 hairline-top font-mono text-caption">
          <span>
            Página {table.getState().pagination.pageIndex + 1} de{" "}
            {table.getPageCount()}
          </span>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="border border-hairline px-2.5 py-1 focus-ring disabled:opacity-50"
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="border border-hairline px-2.5 py-1 focus-ring disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
