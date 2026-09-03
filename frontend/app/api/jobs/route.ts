import { NextRequest } from "next/server";
import { proxy, proxyJsonBody } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function POST(request: NextRequest) {
  return proxyJsonBody("/jobs", request);
}

export async function GET(request: NextRequest) {
  return proxy("/jobs", { search: new URL(request.url).searchParams });
}
