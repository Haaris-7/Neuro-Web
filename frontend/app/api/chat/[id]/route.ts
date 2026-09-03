import { NextRequest } from "next/server";
import { BACKEND_URL, sseHeaders } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await request.text();
  let upstream: Response;
  try {
    upstream = await fetch(`${BACKEND_URL}/chat/${encodeURIComponent(id)}`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body,
      cache: "no-store",
      signal: request.signal,
    });
  } catch {
    return Response.json({ detail: "Chat service unavailable" }, { status: 503 });
  }
  if (!upstream.ok || !upstream.body) {
    const text = await upstream.text();
    return new Response(text, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") ?? "application/json" },
    });
  }
  return new Response(upstream.body, { headers: sseHeaders(upstream) });
}
