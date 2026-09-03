import { NextRequest } from "next/server";
import { proxy } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; path: string[] }> },
) {
  const { id, path } = await params;
  const relative = path.map(encodeURIComponent).join("/");
  return proxy(`/jobs/${encodeURIComponent(id)}/files/${relative}`);
}
