/**
 * Proxy para POST /api/v1/query/chips/explain — narrativa LLM sobre el
 * resultado ya verificado (Hito 1 Fase D, ADR-017).
 */

import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return new NextResponse("Invalid JSON body", { status: 400 });
  }
  const upstream = await fetch(`${API_BASE}/api/v1/query/chips/explain`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!upstream.ok) {
    const text = await upstream.text().catch(() => "");
    return new NextResponse(text || `Backend error ${upstream.status}`, {
      status: upstream.status,
    });
  }
  return NextResponse.json(await upstream.json());
}
