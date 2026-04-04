"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  pipelineStepFromStatus,
  ProgressTracker,
} from "@/components/progress-tracker";

function readJobPayload(data: unknown): {
  status: string;
  error: string | null;
} {
  if (!data || typeof data !== "object") {
    return { status: "", error: null };
  }
  const o = data as Record<string, unknown>;
  const status = String(o.status ?? o.state ?? "");
  const errRaw = o.error ?? o.message ?? o.detail;
  const error = typeof errRaw === "string" ? errRaw : null;
  return { status, error };
}

export default function AnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const id = typeof params.id === "string" ? params.id : "";
  const [status, setStatus] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [failedAtStepIndex, setFailedAtStepIndex] = useState<number | undefined>(
    undefined,
  );
  const [usePolling, setUsePolling] = useState(false);
  const maxReachedRef = useRef(0);

  const applyPayload = useCallback((data: unknown) => {
    const { status: st, error: err } = readJobPayload(data);
    setStatus(st);
    setError(err);
    const step = pipelineStepFromStatus(st);
    const lower = st.toLowerCase();
    if (step >= 0) {
      maxReachedRef.current = Math.max(maxReachedRef.current, step);
    }
    if (lower === "failed" || lower === "error") {
      setFailedAtStepIndex((prev) =>
        prev === undefined ? maxReachedRef.current : prev,
      );
    }
  }, []);

  useEffect(() => {
    if (!id) return;
    let es: EventSource | null = null;
    let pollTimer: ReturnType<typeof setInterval> | null = null;
    let closed = false;

    const startPolling = () => {
      if (pollTimer) return;
      setUsePolling(true);
      pollTimer = setInterval(async () => {
        try {
          const r = await fetch(`/api/jobs/${encodeURIComponent(id)}`);
          if (!r.ok) return;
          const j = (await r.json()) as unknown;
          applyPayload(j);
        } catch {
          return;
        }
      }, 2000);
    };

    (async () => {
      try {
        const r = await fetch(`/api/jobs/${encodeURIComponent(id)}`);
        if (r.ok) {
          const j = (await r.json()) as unknown;
          applyPayload(j);
        }
      } catch {
        startPolling();
      }
    })();

    try {
      es = new EventSource(`/api/jobs/${encodeURIComponent(id)}/stream`);
      const handleEvent = (ev: MessageEvent) => {
        try {
          const parsed = JSON.parse(ev.data) as unknown;
          applyPayload(parsed);
        } catch {
          return;
        }
      };
      es.addEventListener("job", handleEvent);
      es.onmessage = handleEvent;
      es.onerror = () => {
        if (closed) return;
        es?.close();
        es = null;
        startPolling();
      };
    } catch {
      startPolling();
    }

    return () => {
      closed = true;
      es?.close();
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [id, applyPayload]);

  const lower = status.toLowerCase();
  const isReady =
    lower === "ready" || lower === "completed" || lower === "complete" || lower === "done";
  const isFailed = lower === "failed" || lower === "error";

  const handleRetry = () => {
    maxReachedRef.current = 0;
    setFailedAtStepIndex(undefined);
    setError(null);
    setStatus("");
    router.push("/");
  };

  return (
    <div className="relative min-h-screen bg-[#0a0e1a] text-slate-100">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_70%_40%_at_50%_0%,rgb(139_92_246_/_0.12),transparent)]"
        aria-hidden
      />
      <header className="relative z-10 border-b border-slate-800/80 bg-[#0a0e1a]/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-3xl items-center justify-between px-6">
          <Link
            href="/"
            className="text-sm font-medium text-slate-400 transition hover:text-cyan-300"
          >
            ← Back
          </Link>
          {usePolling ? (
            <span className="text-xs uppercase tracking-widest text-amber-400/90">
              Live updates (polling)
            </span>
          ) : (
            <span className="text-xs uppercase tracking-widest text-cyan-400/80">
              Live stream
            </span>
          )}
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-3xl px-6 py-12">
        <h1 className="mb-2 text-2xl font-bold tracking-tight text-slate-50">
          Analysis
        </h1>
        <p className="mb-10 font-mono text-sm text-slate-500">Job {id}</p>

        <div className="rounded-3xl border border-slate-800/90 bg-[#111827]/70 p-8 shadow-[0_0_0_1px_rgb(30_41_59_/_0.6),0_24px_64px_-24px_rgb(0_0_0_/_0.5)] backdrop-blur-sm">
          <ProgressTracker
            status={status}
            error={error}
            failedAtStepIndex={failedAtStepIndex}
          />

          {isReady ? (
            <div className="mt-10 border-t border-slate-800 pt-8 text-center animate-neuro-fade-in">
              <p className="mb-4 text-lg font-semibold text-emerald-300">
                Analysis complete
              </p>
              <p className="mb-6 text-sm text-slate-400">
                Your brain-response report is ready to open.
              </p>
              <Link
                href={`/results/${encodeURIComponent(id)}`}
                className="inline-flex items-center justify-center rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 px-8 py-3 text-sm font-semibold text-white shadow-lg shadow-cyan-500/20 transition hover:brightness-110"
              >
                View results
              </Link>
            </div>
          ) : null}

          {isFailed ? (
            <div className="mt-10 border-t border-slate-800 pt-8 text-center animate-neuro-fade-in">
              <p className="mb-4 text-lg font-semibold text-red-300">
                Something went wrong
              </p>
              <button
                type="button"
                onClick={handleRetry}
                className="inline-flex items-center justify-center rounded-xl border border-slate-600 bg-slate-900/80 px-8 py-3 text-sm font-semibold text-slate-200 transition hover:border-cyan-500/40 hover:text-cyan-200"
              >
                Try another URL
              </button>
            </div>
          ) : null}
        </div>
      </main>
    </div>
  );
}
