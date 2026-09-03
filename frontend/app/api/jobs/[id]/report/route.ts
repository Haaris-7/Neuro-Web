import { NextRequest } from "next/server";
import { proxy } from "@/lib/backend";

export const dynamic = "force-dynamic";

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  return proxy(`/jobs/${encodeURIComponent(id)}/report`);
}
