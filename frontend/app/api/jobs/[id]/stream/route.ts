import { NextRequest } from "next/server";
import { BACKEND_URL, sseHeaders } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const lastId = request.headers.get("last-event-id");
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/jobs/${encodeURIComponent(id)}/stream`, {
      headers: {
        Accept: "text/event-stream",
        ...(lastId ? { "Last-Event-ID": lastId } : {}),
      },
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return new Response("Backend unavailable", { status: 503 });
  }
  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.statusText || "Upstream error", {
      status: upstream.status || 502,
    });
  }
  return new Response(upstream.body, { headers: sseHeaders(upstream) });
}
