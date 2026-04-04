import { NextRequest } from "next/server";

export const dynamic = "force-dynamic";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const lastId = request.headers.get("last-event-id");
  const upstream = await fetch(
    `http://localhost:8000/jobs/${encodeURIComponent(id)}/stream`,
    {
      headers: {
        Accept: "text/event-stream",
        ...(lastId ? { "Last-Event-ID": lastId } : {}),
      },
      cache: "no-store",
    },
  );

  if (!upstream.ok || !upstream.body) {
    return new Response(upstream.statusText || "Upstream error", {
      status: upstream.status || 502,
    });
  }

  return new Response(upstream.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
