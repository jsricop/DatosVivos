"use client";

import {
  type ColumnFiltersState,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  type SortingState,
  useReactTable,
} from "@tanstack/react-table";
import { useCallback, useMemo, useState } from "react";

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
 * Funcionalidad ciudadana + periodista:
 * - Search global (matchea cualquier columna).
 * - Sort por columna con `aria-sort` + teclado.
 * - Filtros por columna individual (toggle "Filtros avanzados").
 * - Descarga CSV de las filas actualmente visibles.
 * - Paginación.
 *
 * Tipografía Plex Mono tabular-nums en celdas numéricas. Regletas hairline,
 * sin zebra striping.
 */
export function DataTable({
  columns,
  rows,
  caption,
  pageSize = 25,
  downloadFilename = "rows.csv",
}: DataTableProps) {
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [filtersOpen, setFiltersOpen] = useState(false);

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
        filterFn: "includesString" as const,
      })),
    [columns],
  );

  const table = useReactTable({
    data: rows,
    columns: tableColumns,
    state: { globalFilter, sorting, columnFilters },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    globalFilterFn: "includesString",
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    initialState: { pagination: { pageSize } },
  });

  const matchCount = table.getFilteredRowModel().rows.length;
  const activeColumnFilters = columnFilters.filter((f) => Boolean(f.value)).length;

  const downloadCsv = useCallback(() => {
    const escape = (v: unknown) => {
      const s = v === null || v === undefined ? "" : String(v);
      return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
    };
    // Exporta solo las filas filtradas, ordenadas (el usuario ve lo que descarga).
    const sortedFiltered = table.getSortedRowModel().rows.map((r) => r.original);
    const csv = [
      columns.join(","),
      ...sortedFiltered.map((r) => columns.map((c) => escape(r[c])).join(",")),
    ].join("\n");
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = downloadFilename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [columns, downloadFilename, table]);

  function clearAllFilters() {
    setGlobalFilter("");
    setColumnFilters([]);
  }

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
      className="rounded-[var(--radius-2)] border border-hairline overflow-auto max-h-[60vh]"
    >
      <div className="flex flex-wrap items-center gap-4 px-4 py-3 hairline-bottom bg-bg-elev sticky top-0 z-10">
        <div className="flex items-center gap-2 flex-1 min-w-[200px]">
          <span aria-hidden="true" className="text-ink-2">
            <Icon name="search" size={16} />
          </span>
          <label htmlFor="datatable-search" className="sr-only">
            Buscar en la tabla
          </label>
          <input
            id="datatable-search"
            type="search"
            value={globalFilter}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder={`Buscar en ${rows.length.toLocaleString("es-CO")} filas…`}
            className="flex-1 min-w-0 bg-transparent font-sans text-body-sm text-ink focus-ring"
          />
        </div>
        <span className="text-kicker [font-variant-numeric:tabular-nums]">
          {matchCount.toLocaleString("es-CO")} de{" "}
          {rows.length.toLocaleString("es-CO")}
        </span>
        <button
          type="button"
          onClick={() => setFiltersOpen((v) => !v)}
          aria-pressed={filtersOpen}
          aria-controls="datatable-column-filters"
          className="inline-flex items-center gap-2 rounded-[var(--radius-1)] border border-accent px-3 py-1.5 font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] text-accent hover:bg-bg-overlay focus-ring"
        >
          <Icon name="filter" size={14} aria-hidden />
          <span>Filtros{activeColumnFilters > 0 ? ` (${activeColumnFilters})` : ""}</span>
        </button>
        {globalFilter || activeColumnFilters > 0 ? (
          <button
            type="button"
            onClick={clearAllFilters}
            className="font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] text-ink-2 underline focus-ring"
          >
            Limpiar
          </button>
        ) : null}
        <button
          type="button"
          onClick={downloadCsv}
          className="inline-flex items-center gap-2 rounded-[var(--radius-1)] border border-accent px-3 py-1.5 font-mono text-[length:var(--type-kicker)] uppercase tracking-[0.08em] text-accent hover:bg-bg-overlay focus-ring"
          aria-label="Descargar CSV con las filas visibles"
        >
          <Icon name="download" size={14} aria-hidden />
          <span>Descargar CSV</span>
        </button>
      </div>
      <table className="min-w-full" id="datatable-column-filters">
        {caption ? (
          <caption className="px-4 py-3 font-mono text-caption text-ink-2 text-start caption-top">
            {caption}
          </caption>
        ) : null}
        <thead>
          {table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>
              {hg.headers.map((header) => {
                const sortDir = header.column.getIsSorted();
                const ariaSort =
                  sortDir === "asc"
                    ? "ascending"
                    : sortDir === "desc"
                      ? "descending"
                      : "none";
                return (
                  <th
                    key={header.id}
                    scope="col"
                    aria-sort={ariaSort}
                    tabIndex={0}
                    onClick={header.column.getToggleSortingHandler()}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        header.column.toggleSorting();
                      }
                    }}
                    className="cursor-pointer select-none focus-ring"
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )}
                      <SortIndicator dir={sortDir} />
                    </span>
                  </th>
                );
              })}
            </tr>
          ))}
          {filtersOpen ? (
            <tr className="hairline-bottom">
              {table.getHeaderGroups()[0]?.headers.map((header) => (
                <th
                  key={`${header.id}-filter`}
                  scope="col"
                  className="px-3 py-2 align-top"
                >
                  <ColumnFilterInput
                    column={header.column}
                    onActivate={() => {
                      /* nothing; binding live via state */
                    }}
                  />
                </th>
              ))}
            </tr>
          ) : null}
        </thead>
        <tbody>
          {table.getRowModel().rows.length === 0 ? (
            <tr>
              <td
                colSpan={columns.length}
                className="font-sans text-body-sm text-ink-muted text-center py-6"
              >
                Ninguna fila coincide con los filtros actuales.
              </td>
            </tr>
          ) : (
            table.getRowModel().rows.map((row) => (
              <tr key={row.id}>
                {row.getVisibleCells().map((cell) => {
                  const value = cell.getValue();
                  const isNumeric =
                    typeof value === "number" ||
                    (typeof value === "string" && /^-?\d/.test(value));
                  return (
                    <td
                      key={cell.id}
                      className={
                        isNumeric
                          ? "font-mono [font-variant-numeric:tabular-nums]"
                          : "font-sans"
                      }
                    >
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  );
                })}
              </tr>
            ))
          )}
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
              className="rounded-[var(--radius-1)] border border-hairline px-2.5 py-1 hover:border-accent focus-ring disabled:opacity-50"
            >
              Anterior
            </button>
            <button
              type="button"
              onClick={() => table.nextPage()}
              disabled={!table.getCanNextPage()}
              className="rounded-[var(--radius-1)] border border-hairline px-2.5 py-1 hover:border-accent focus-ring disabled:opacity-50"
            >
              Siguiente
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

function SortIndicator({ dir }: { dir: false | "asc" | "desc" }) {
  if (!dir)
    return (
      <span aria-hidden className="text-ink-muted font-mono text-[10px]">
        ↕
      </span>
    );
  return (
    <span aria-hidden className="text-accent font-mono text-[10px]">
      {dir === "asc" ? "▴" : "▾"}
    </span>
  );
}

type ColumnLike = {
  id: string;
  getFilterValue: () => unknown;
  setFilterValue: (v: unknown) => void;
};

function ColumnFilterInput({
  column,
  onActivate,
}: {
  column: ColumnLike;
  onActivate: () => void;
}) {
  const value = (column.getFilterValue() ?? "") as string;
  return (
    <input
      type="search"
      value={value}
      onChange={(e) => {
        column.setFilterValue(e.target.value || undefined);
        if (e.target.value) onActivate();
      }}
      placeholder="filtrar…"
      aria-label={`Filtro de columna ${column.id}`}
      className="w-full border border-hairline bg-bg px-2 py-1 font-mono text-caption text-ink focus-ring"
    />
  );
}
