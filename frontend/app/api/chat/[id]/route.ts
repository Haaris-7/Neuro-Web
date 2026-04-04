import { NextRequest } from "next/server";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const body = await request.text();
  const url = `http://localhost:8000/chat/${encodeURIComponent(id)}`;

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
    });

    if (!res.ok) {
      const text = await res.text();
      return new Response(text, {
        status: res.status,
        headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
      });
    }

    if (res.headers.get("content-type")?.includes("text/event-stream")) {
      return new Response(res.body, {
        status: 200,
        headers: {
          "Content-Type": "text/event-stream",
          "Cache-Control": "no-cache",
          Connection: "keep-alive",
        },
      });
    }

    const text = await res.text();
    return new Response(text, {
      status: 200,
      headers: { "Content-Type": res.headers.get("content-type") || "application/json" },
    });
  } catch {
    return new Response(
      JSON.stringify({ error: "Chat service unavailable" }),
      { status: 503, headers: { "Content-Type": "application/json" } },
    );
  }
}
