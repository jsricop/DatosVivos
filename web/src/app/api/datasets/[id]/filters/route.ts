/**
 * Proxy para GET /api/v1/datasets/{id}/filters — columnas filtrables del
 * dataset con sus valores reales (perfil de la bodega, ADR-024).
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const upstream = await fetch(
    `${API_BASE}/api/v1/datasets/${encodeURIComponent(id)}/filters`,
    { headers: { Accept: "application/json" } },
  );
  if (!upstream.ok) {
    const text = await upstream.text().catch(() => "");
    return new NextResponse(text || `Backend error ${upstream.status}`, {
      status: upstream.status,
    });
  }
  return NextResponse.json(await upstream.json());
}
