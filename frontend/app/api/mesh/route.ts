import { readFile } from "fs/promises";
import path from "path";

const DATA_DIR = path.resolve(process.cwd(), "..", "data");

export async function GET() {
  const glbPath = path.join(DATA_DIR, "cache", "fsaverage5.glb");

  try {
    const buf = await readFile(glbPath);
    return new Response(buf, {
      status: 200,
      headers: {
        "Content-Type": "model/gltf-binary",
        "Cache-Control": "public, max-age=86400, immutable",
      },
    });
  } catch {
    return new Response("Brain mesh not found. Run `make setup` to generate.", {
      status: 404,
    });
  }
}

export const dynamic = "force-static";
