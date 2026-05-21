/**
 * Proxy SSE entre el navegador y el FastAPI Python (api/).
 *
 * Modelo: el cliente abre POST /api/proxy/query (rewrite a /api/v1/query
 * cuando viene como GET para EventSource; o stream directo cuando es POST).
 * Aquí re-emitimos los chunks tal cual.
 */

import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const API_BASE = process.env.API_BASE_URL ?? "http://localhost:8000";

export async function POST(req: NextRequest) {
  let body: unknown;
  try {
    body = await req.json();
  } catch {
    return new Response("Invalid JSON body", { status: 400 });
  }

  const upstream = await fetch(`${API_BASE}/api/v1/query`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify(body),
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(`Backend error ${upstream.status}`, {
      status: upstream.status,
    });
  }

  const stream = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          controller.enqueue(value);
        }
      } finally {
        controller.close();
      }
    },
    cancel() {
      upstream.body?.cancel();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
