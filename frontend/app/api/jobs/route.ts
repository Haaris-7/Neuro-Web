import { NextRequest } from "next/server";

const BACKEND = "http://localhost:8000/jobs";

export async function POST(request: NextRequest) {
  const body = await request.text();
  const ct = request.headers.get("content-type");
  const res = await fetch(BACKEND, {
    method: "POST",
    headers: {
      ...(ct ? { "Content-Type": ct } : { "Content-Type": "application/json" }),
    },
    body,
    cache: "no-store",
  });
  const text = await res.text();
  const outCt = res.headers.get("content-type") || "application/json";
  return new Response(text, { status: res.status, headers: { "Content-Type": outCt } });
}

export async function GET(request: NextRequest) {
  const url = new URL(request.url);
  const target = new URL(BACKEND);
  url.searchParams.forEach((v, k) => target.searchParams.set(k, v));
  const res = await fetch(target.toString(), { cache: "no-store" });
  const text = await res.text();
  const outCt = res.headers.get("content-type") || "application/json";
  return new Response(text, { status: res.status, headers: { "Content-Type": outCt } });
}
