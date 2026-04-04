import { NextRequest } from "next/server";

function backendUrl(id: string) {
  return `http://localhost:8000/jobs/${encodeURIComponent(id)}`;
}

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const res = await fetch(backendUrl(id), { cache: "no-store" });
  const text = await res.text();
  const outCt = res.headers.get("content-type") || "application/json";
  return new Response(text, { status: res.status, headers: { "Content-Type": outCt } });
}

export async function DELETE(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
) {
  const { id } = await context.params;
  const res = await fetch(backendUrl(id), { method: "DELETE", cache: "no-store" });
  const text = await res.text();
  const outCt = res.headers.get("content-type") || "application/json";
  return new Response(text, { status: res.status, headers: { "Content-Type": outCt } });
}
