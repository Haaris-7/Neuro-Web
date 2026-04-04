import { NextRequest } from "next/server";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const url = `http://localhost:8000/jobs/${encodeURIComponent(id)}/report`;
  const res = await fetch(url, { cache: "no-store" });
  const text = await res.text();
  const ct = res.headers.get("content-type") || "application/json";
  return new Response(text, { status: res.status, headers: { "Content-Type": ct } });
}
