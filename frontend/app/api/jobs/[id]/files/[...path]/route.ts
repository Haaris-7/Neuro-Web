import { NextRequest } from "next/server";
import { readFile } from "fs/promises";
import path from "path";

const DATA_DIR = path.resolve(process.cwd(), "..", "data");

const MIME_TYPES: Record<string, string> = {
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".webm": "video/webm",
  ".json": "application/json",
  ".glb": "model/gltf-binary",
  ".npy": "application/octet-stream",
};

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string; path: string[] }> },
) {
  const { id, path: segments } = await context.params;
  const filename = segments.join("/");

  const subdirs = ["captures", "predictions", "reports"];
  let filePath: string | null = null;

  for (const sub of subdirs) {
    const candidate = path.join(DATA_DIR, sub, id, filename);
    const resolved = path.resolve(candidate);
    if (resolved.startsWith(path.join(DATA_DIR, sub, id))) {
      filePath = resolved;
      break;
    }
  }

  if (!filePath) {
    return new Response("Not found", { status: 404 });
  }

  try {
    const buf = await readFile(filePath);
    const ext = path.extname(filePath).toLowerCase();
    const contentType = MIME_TYPES[ext] || "application/octet-stream";

    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=3600, immutable",
      },
    });
  } catch {
    return new Response("Not found", { status: 404 });
  }
}
