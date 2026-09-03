import { NextRequest } from "next/server";
import { proxy } from "@/lib/backend";

export const dynamic = "force-dynamic";

type Params = { params: Promise<{ id: string }> };

export async function GET(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxy(`/jobs/${encodeURIComponent(id)}`);
}

export async function DELETE(_request: NextRequest, { params }: Params) {
  const { id } = await params;
  return proxy(`/jobs/${encodeURIComponent(id)}`, { method: "DELETE" });
}
