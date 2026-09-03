"use client";

import { useEffect, useState } from "react";
import type { HealthResponse } from "@/lib/types";

type Status =
  | { kind: "loading" }
  | { kind: "offline" }
  | { kind: "ok"; health: HealthResponse };

export function BackendStatus() {
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const poll = async () => {
      try {
        const res = await fetch("/api/health", { cache: "no-store" });
        if (!res.ok) throw new Error(String(res.status));
        const health = (await res.json()) as HealthResponse;
        if (!cancelled) setStatus({ kind: "ok", health });
        if (!cancelled && health.model_loading) timer = setTimeout(poll, 5000);
      } catch {
        if (!cancelled) setStatus({ kind: "offline" });
        if (!cancelled) timer = setTimeout(poll, 10000);
      }
    };
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (status.kind === "loading") return null;

  if (status.kind === "offline") {
    return (
      <Banner tone="danger">
        Backend is not reachable. Start it with <code>make run-backend</code>.
      </Banner>
    );
  }

  const { health } = status;
  if (health.inference_backend === "mock") {
    return (
      <Banner tone="warning">
        Synthetic inference mode: results are placeholders generated without TRIBE v2. Set{" "}
        <code>INFERENCE_BACKEND=tribe</code> on a CUDA machine for real predictions.
      </Banner>
    );
  }
  if (health.model_loading) {
    return (
      <Banner tone="info">
        Loading TRIBE v2 on the GPU. Analyses you submit now will start once the model is ready.
      </Banner>
    );
  }
  if (!health.inference_ready) {
    return (
      <Banner tone="danger">
        Brain analysis is unavailable: {health.error ?? "TRIBE v2 failed to load."}
      </Banner>
    );
  }
  return (
    <Banner tone="ok">
      TRIBE v2 ready · {health.modalities.join(" + ")}
      {health.llm_available ? ` · chat via ${health.llm_provider}` : ""}
    </Banner>
  );
}

const TONES = {
  ok: "border-emerald-500/20 bg-emerald-500/5 text-emerald-300",
  info: "border-cyan-500/20 bg-cyan-500/5 text-cyan-200",
  warning: "border-amber-500/30 bg-amber-500/10 text-amber-200",
  danger: "border-red-500/30 bg-red-500/10 text-red-200",
} as const;

function Banner({ tone, children }: { tone: keyof typeof TONES; children: React.ReactNode }) {
  return (
    <p
      className={`mt-4 max-w-2xl rounded-xl border px-4 py-2 text-center text-xs leading-relaxed ${TONES[tone]} [&_code]:rounded [&_code]:bg-black/30 [&_code]:px-1`}
      role="status"
    >
      {children}
    </p>
  );
}
