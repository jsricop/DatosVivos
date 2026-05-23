/**
 * Proxy GET /api/chips/refine → backend /api/v1/chips/refine.
 *
 * Capa 2 de chips: sub-tags refinadores del subset filtrado por chips capa 1.
 * Ver `web/src/components/SubtagsBar.tsx`.
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function GET(req: NextRequest) {
  const qs = req.nextUrl.searchParams.toString();
  const upstream = await fetch(`${API_BASE}/api/v1/chips/refine?${qs}`, {
    method: "GET",
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  if (!upstream.ok) {
    return new NextResponse(`Backend error ${upstream.status}`, {
      status: upstream.status,
    });
  }
  return NextResponse.json(await upstream.json());
}
