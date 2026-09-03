import { NextRequest } from "next/server";

export const BACKEND_URL = (
  process.env.BACKEND_URL ?? "http://localhost:8000"
).replace(/\/$/, "");

export function backendUrl(path: string, search?: URLSearchParams): string {
  const query = search && [...search.keys()].length ? `?${search.toString()}` : "";
  return `${BACKEND_URL}${path}${query}`;
}

const HOP_BY_HOP = new Set([
  "connection",
  "keep-alive",
  "transfer-encoding",
  "content-encoding",
  "content-length",
]);

function passthroughHeaders(upstream: Response): Headers {
  const headers = new Headers();
  upstream.headers.forEach((value, key) => {
    if (!HOP_BY_HOP.has(key.toLowerCase())) headers.set(key, value);
  });
  return headers;
}

/** Forward a request to the backend and stream the response back unchanged. */
export async function proxy(
  path: string,
  init: RequestInit & { search?: URLSearchParams } = {},
): Promise<Response> {
  const { search, ...rest } = init;
  let upstream: Response;
  try {
    upstream = await fetch(backendUrl(path, search), { cache: "no-store", ...rest });
  } catch {
    return Response.json(
      { detail: `Backend unavailable at ${BACKEND_URL}` },
      { status: 503 },
    );
  }
  return new Response(upstream.body, {
    status: upstream.status,
    headers: passthroughHeaders(upstream),
  });
}

export async function proxyJsonBody(path: string, request: NextRequest, method = "POST") {
  const body = await request.text();
  return proxy(path, {
    method,
    body,
    headers: { "Content-Type": request.headers.get("content-type") ?? "application/json" },
  });
}

export function sseHeaders(upstream: Response): Headers {
  const headers = passthroughHeaders(upstream);
  headers.set("Content-Type", "text/event-stream");
  headers.set("Cache-Control", "no-cache, no-transform");
  headers.set("Connection", "keep-alive");
  headers.set("X-Accel-Buffering", "no");
  return headers;
}
