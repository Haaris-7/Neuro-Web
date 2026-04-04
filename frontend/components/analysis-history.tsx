"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import type { JobResponse } from "@/lib/types";

export function AnalysisHistory() {
  const [jobs, setJobs] = useState<JobResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const res = await fetch("/api/jobs");
      if (res.ok) {
        const data = (await res.json()) as JobResponse[];
        setJobs(data);
      }
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleDelete = useCallback(
    async (id: string) => {
      if (!confirm("Delete this analysis? This cannot be undone.")) return;
      setDeleting(id);
      try {
        const res = await fetch(`/api/jobs/${encodeURIComponent(id)}`, {
          method: "DELETE",
        });
        if (res.ok || res.status === 204) {
          setJobs((prev) => prev.filter((j) => j.id !== id));
        }
      } catch {
        /* ignore */
      } finally {
        setDeleting(null);
      }
    },
    [],
  );

  const formatDate = (iso: string) => {
    try {
      return new Date(iso).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return iso;
    }
  };

  const getHostname = (url: string) => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  };

  const getStatusBadge = (status: string) => {
    const s = status.toLowerCase();
    if (s === "ready" || s === "completed") {
      return (
        <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
          Ready
        </span>
      );
    }
    if (s === "failed") {
      return (
        <span className="rounded-full bg-red-500/10 px-2 py-0.5 text-[10px] font-semibold text-red-400">
          Failed
        </span>
      );
    }
    return (
      <span className="rounded-full bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-400">
        {status}
      </span>
    );
  };

  const getScores = (job: JobResponse) => {
    const meta = job.capture_metadata as Record<string, unknown> | null;
    const scoring = meta?.scoring as Record<string, unknown> | null;
    if (!scoring) return null;
    return {
      attention: Number(scoring.attention_score ?? 0),
      emotion: Number(scoring.emotion_score ?? 0),
      impact: Number(scoring.impact_score ?? 0),
    };
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-20 animate-pulse rounded-2xl bg-slate-800/30"
          />
        ))}
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-slate-800/40">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="#475569"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M12 8v4l3 3" />
            <circle cx="12" cy="12" r="10" />
          </svg>
        </div>
        <p className="mb-2 text-sm font-medium text-slate-400">
          No analyses yet
        </p>
        <p className="mb-6 text-xs text-slate-600">
          Paste a URL on the home page to get started
        </p>
        <Link
          href="/"
          className="rounded-xl bg-gradient-to-r from-cyan-500 to-violet-600 px-6 py-2.5 text-xs font-semibold text-white transition hover:brightness-110"
        >
          Analyze a website
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {jobs.map((job) => {
        const scores = getScores(job);
        const isReady = ["ready", "completed"].includes(
          job.status.toLowerCase(),
        );

        return (
          <div
            key={job.id}
            className="group flex items-center gap-4 rounded-2xl border border-slate-800/60 bg-[#111827]/40 px-5 py-4 transition hover:border-slate-700/60 hover:bg-[#111827]/60"
          >
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2">
                {isReady ? (
                  <Link
                    href={`/results/${encodeURIComponent(job.id)}`}
                    className="truncate text-sm font-semibold text-slate-200 transition hover:text-cyan-300"
                  >
                    {getHostname(job.url)}
                  </Link>
                ) : (
                  <span className="truncate text-sm font-semibold text-slate-400">
                    {getHostname(job.url)}
                  </span>
                )}
                {getStatusBadge(job.status)}
              </div>
              <div className="mt-1 flex items-center gap-3 text-[10px] text-slate-600">
                <span>{formatDate(job.created_at)}</span>
                <span className="max-w-[200px] truncate font-mono">
                  {job.id.slice(0, 8)}
                </span>
              </div>
            </div>

            {scores && (
              <div className="hidden items-center gap-4 sm:flex">
                <div className="text-center">
                  <p className="font-mono text-sm font-bold text-cyan-400">
                    {scores.attention.toFixed(1)}
                  </p>
                  <p className="text-[9px] uppercase tracking-widest text-slate-600">
                    Att
                  </p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-sm font-bold text-violet-400">
                    {scores.emotion.toFixed(1)}
                  </p>
                  <p className="text-[9px] uppercase tracking-widest text-slate-600">
                    Emo
                  </p>
                </div>
                <div className="text-center">
                  <p className="font-mono text-sm font-bold text-slate-300">
                    {scores.impact.toFixed(1)}
                  </p>
                  <p className="text-[9px] uppercase tracking-widest text-slate-600">
                    Impact
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-center gap-2">
              {isReady && (
                <Link
                  href={`/results/${encodeURIComponent(job.id)}`}
                  className="rounded-lg bg-slate-800/60 px-3 py-1.5 text-[10px] font-semibold text-slate-300 transition hover:bg-slate-700/60 hover:text-cyan-200"
                >
                  View
                </Link>
              )}
              <button
                onClick={() => handleDelete(job.id)}
                disabled={deleting === job.id}
                className="rounded-lg px-2 py-1.5 text-slate-600 transition hover:bg-red-500/10 hover:text-red-400 disabled:opacity-30"
                title="Delete analysis"
              >
                {deleting === job.id ? (
                  <span className="inline-block h-3.5 w-3.5 rounded-full border-2 border-red-400/30 border-t-red-400 animate-neuro-spin" />
                ) : (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.5"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
