"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { BackendStatus } from "@/components/backend-status";
import { UrlInput, validateHttpUrl } from "@/components/url-input";

const FEATURES = [
  {
    title: "Brain Mapping",
    description:
      "Meta's TRIBE v2 predicts fMRI-like responses across 20,000+ cortical vertices from a scrolling recording of the page, on your local GPU.",
    icon: (
      <svg
        className="h-7 w-7"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 2a7 7 0 0 0-7 7c0 3 2 5.5 4 7.5S12 20 12 22c0-2 1-3.5 3-5.5s4-4.5 4-7.5a7 7 0 0 0-7-7Z" />
        <path d="M12 2v4M9 6l6 4M9 10l6-4" />
      </svg>
    ),
  },
  {
    title: "Dark Pattern Detection",
    description:
      "Rule-based detectors flag urgency, confirmshaming, pre-checked consent, hidden costs, misdirection and forced continuity.",
    icon: (
      <svg
        className="h-7 w-7"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="M12 9v4M12 17h.01" />
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
      </svg>
    ),
  },
  {
    title: "Privacy First",
    description:
      "Everything runs locally on your machine. No cloud, no tracking, no data leaves your computer.",
    icon: (
      <svg
        className="h-7 w-7"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
        <path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
    ),
  },
];

export default function Home() {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = useCallback(async () => {
    const trimmed = url.trim();
    if (!validateHttpUrl(trimmed)) {
      setError("Please enter a valid URL starting with http:// or https://");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: trimmed }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        const detail =
          body && typeof body === "object" && "detail" in body
            ? String((body as Record<string, unknown>).detail)
            : `Request failed (${res.status})`;
        setError(detail);
        setLoading(false);
        return;
      }
      const job = (await res.json()) as { id: string };
      router.push(`/analysis/${encodeURIComponent(job.id)}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
      setLoading(false);
    }
  }, [url, router]);

  return (
    <div className="relative min-h-screen bg-[#0a0e1a] text-slate-100">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_50%_at_50%_-10%,rgb(139_92_246_/_0.18),transparent)]"
        aria-hidden
      />

      <main className="relative z-10 flex flex-col items-center px-6">
        <div className="flex min-h-[70vh] max-w-3xl flex-col items-center justify-center text-center">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-slate-700/70 bg-slate-900/60 px-4 py-1.5 text-xs font-medium text-slate-400 backdrop-blur-sm">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
            Powered by Meta TRIBE v2 · Local GPU Inference
          </div>

          <h1 className="mb-4 text-5xl font-extrabold tracking-tight sm:text-6xl lg:text-7xl">
            <span className="bg-gradient-to-r from-cyan-300 via-blue-400 to-violet-500 bg-clip-text text-transparent">
              Neuro Web
            </span>
          </h1>

          <p className="mb-2 text-xl font-medium text-slate-300 sm:text-2xl">
            See how websites affect your brain
          </p>

          <p className="mb-12 max-w-xl text-base leading-relaxed text-slate-500">
            Paste any URL and get a neuroscience-grounded analysis of how the site
            captures attention, triggers emotions, and uses manipulative design patterns —
            all running locally on your GPU.
          </p>

          <UrlInput
            value={url}
            onChange={setUrl}
            onSubmit={handleSubmit}
            loading={loading}
            error={error}
          />
          <BackendStatus />
        </div>

        <section className="mx-auto mt-8 grid w-full max-w-4xl grid-cols-1 gap-5 pb-20 sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="group rounded-2xl border border-slate-800/80 bg-[#111827]/60 p-6 backdrop-blur-sm transition hover:border-slate-700 hover:bg-[#111827]/80"
            >
              <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-cyan-500/15 to-violet-600/15 text-cyan-400 ring-1 ring-cyan-400/15 transition group-hover:text-cyan-300 group-hover:ring-cyan-400/30">
                {f.icon}
              </div>
              <h3 className="mb-2 text-base font-semibold text-slate-200">
                {f.title}
              </h3>
              <p className="text-sm leading-relaxed text-slate-500">
                {f.description}
              </p>
            </div>
          ))}
        </section>
      </main>
    </div>
  );
}
