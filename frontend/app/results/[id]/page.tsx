"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import {
  jobFileUrl,
  type AnalysisReport,
  type AtlasData,
  type HealthResponse,
} from "@/lib/types";
import type { ColormapName } from "@/lib/colormaps";
import { ReportCard } from "@/components/results/report-card";
import { WebsiteOverlay } from "@/components/results/website-overlay";
import { ScrollTimeline } from "@/components/results/scroll-timeline";
import { BrainHeatmapFallback } from "@/components/results/brain-heatmap-fallback";
import { ChatbotPanel } from "@/components/results/chatbot-panel";

const BrainHeatmap = dynamic(
  () =>
    import("@/components/results/brain-heatmap").then(
      (mod) => mod.BrainHeatmap,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-[500px] items-center justify-center rounded-2xl border border-slate-800/40 bg-[#060a14]">
        <div className="flex flex-col items-center gap-3">
          <span className="inline-block h-6 w-6 rounded-full border-2 border-cyan-400/30 border-t-cyan-400 animate-neuro-spin" />
          <span className="text-xs text-slate-500">Loading 3D brain...</span>
        </div>
      </div>
    ),
  },
);

type Tab = "report" | "brain" | "overlay" | "timeline";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  {
    key: "report",
    label: "Report Card",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
        <path d="M14 2v6h6M16 13H8M16 17H8M10 9H8" />
      </svg>
    ),
  },
  {
    key: "brain",
    label: "Brain Heatmap",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a7 7 0 0 0-7 7c0 3 2 5.5 4 7.5S12 20 12 22c0-2 1-3.5 3-5.5s4-4.5 4-7.5a7 7 0 0 0-7-7Z" />
        <path d="M12 2v4M9 6l6 4M9 10l6-4" />
      </svg>
    ),
  },
  {
    key: "overlay",
    label: "Website Overlay",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M3 9h18M9 21V9" />
      </svg>
    ),
  },
  {
    key: "timeline",
    label: "Scroll Timeline",
    icon: (
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M3 3v18h18" />
        <path d="m19 9-5 5-4-4-3 3" />
      </svg>
    ),
  },
];

function LoadingSkeleton() {
  return (
    <div className="space-y-6 py-8">
      <div className="flex flex-col items-center gap-4">
        <div className="h-32 w-32 animate-pulse rounded-full bg-slate-800/50" />
        <div className="h-4 w-48 animate-pulse rounded-lg bg-slate-800/50" />
        <div className="h-3 w-64 animate-pulse rounded-lg bg-slate-800/40" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="h-28 animate-pulse rounded-2xl bg-slate-800/30" />
        <div className="h-28 animate-pulse rounded-2xl bg-slate-800/30" />
      </div>
      <div className="h-20 animate-pulse rounded-2xl bg-slate-800/20" />
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex min-h-[400px] flex-col items-center justify-center gap-4 py-12">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-500/10">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ef4444" strokeWidth="1.5" strokeLinecap="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 8v4M12 16h.01" />
        </svg>
      </div>
      <p className="max-w-md text-center text-sm text-slate-400">{message}</p>
      <button
        onClick={onRetry}
        className="rounded-xl border border-slate-700 bg-slate-900/80 px-6 py-2 text-xs font-semibold text-slate-300 transition hover:border-cyan-500/30 hover:text-cyan-200"
      >
        Retry
      </button>
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const jobId = typeof params.id === "string" ? params.id : "";

  const [report, setReport] = useState<AnalysisReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("report");
  const [chatOpen, setChatOpen] = useState(false);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [webglAvailable, setWebglAvailable] = useState(true);
  const [atlas, setAtlas] = useState<AtlasData | null>(null);

  const fetchReport = useCallback(async () => {
    if (!jobId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/report`);
      if (!res.ok) {
        if (res.status === 409) {
          setError("Analysis is still in progress. Please wait and try again.");
        } else {
          setError(`Failed to load report (${res.status})`);
        }
        return;
      }
      const data = (await res.json()) as AnalysisReport;
      setReport(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load report");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchReport();
  }, [fetchReport]);

  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const options = { failIfMajorPerformanceCaveat: true };
      const gl = canvas.getContext("webgl2", options) || canvas.getContext("webgl", options);
      setWebglAvailable(!!gl);
      (gl as WebGLRenderingContext | null)?.getExtension("WEBGL_lose_context")?.loseContext();
    } catch {
      setWebglAvailable(false);
    }
  }, []);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => (r.ok ? (r.json() as Promise<HealthResponse>) : null))
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));
  }, []);

  useEffect(() => {
    if (!webglAvailable) return;
    fetch("/api/atlas")
      .then((r) => (r.ok ? (r.json() as Promise<AtlasData>) : null))
      .then((data) => setAtlas(data))
      .catch(() => setAtlas(null));
  }, [webglAvailable]);

  const screenshotUrl = useMemo(() => jobFileUrl(jobId, "page.png"), [jobId]);
  const activationUrl = useMemo(
    () => (report ? jobFileUrl(jobId, report.vertex_activation.file) : ""),
    [jobId, report],
  );
  const timeLabels = useMemo(
    () => report?.timeline.series.map((p) => p.time_s) ?? [],
    [report],
  );
  const colormap = (report?.metadata.colormap as ColormapName | undefined) ?? "viridis";
  const llmAvailable = health?.llm_available ?? false;
  const isMock = report?.metadata.inference_backend === "mock";

  const hostname = useMemo(() => {
    if (!report) return "";
    try {
      return new URL(report.url).hostname;
    } catch {
      return report.url;
    }
  }, [report]);

  return (
    <div className="relative min-h-screen bg-[#0a0e1a] text-slate-100">
      {/* Background */}
      <div
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_80%_40%_at_50%_0%,rgb(139_92_246_/_0.08),transparent)]"
        aria-hidden
      />
      <div className="pointer-events-none fixed inset-0 noise-overlay" aria-hidden />

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#0a0e1a]/90 backdrop-blur-lg">
        <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-sm font-medium text-slate-500 transition hover:text-cyan-300"
            >
              ← Home
            </Link>
            <span className="h-4 w-px bg-slate-800" />
            {report && (
              <div className="flex items-center gap-2">
                <span className="max-w-[200px] truncate text-sm font-medium text-slate-300">
                  {hostname}
                </span>
                <span className="rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-semibold text-emerald-400">
                  Complete
                </span>
                {isMock && (
                  <span className="rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] font-semibold text-amber-300">
                    Mock inference
                  </span>
                )}
              </div>
            )}
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/history"
              className="text-xs text-slate-500 transition hover:text-slate-300"
            >
              History
            </Link>
            {llmAvailable && (
              <button
                onClick={() => setChatOpen(true)}
                className="flex items-center gap-1.5 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-300 transition hover:border-violet-500/40 hover:bg-violet-500/15"
              >
                <svg
                  width="12"
                  height="12"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />
                </svg>
                Ask AI
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Tab bar */}
      {report && (
        <div className="sticky top-14 z-20 border-b border-slate-800/60 bg-[#0a0e1a]/80 backdrop-blur-md">
          <div className="mx-auto flex max-w-7xl gap-1 px-6 py-2">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-medium transition ${
                  activeTab === tab.key
                    ? "bg-slate-800/80 text-slate-100 shadow-sm"
                    : "text-slate-500 hover:bg-slate-800/30 hover:text-slate-300"
                }`}
              >
                <span
                  className={
                    activeTab === tab.key ? "text-cyan-400" : "text-slate-600"
                  }
                >
                  {tab.icon}
                </span>
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Content */}
      <main className="relative z-10 mx-auto max-w-7xl px-6 py-6">
        {loading && <LoadingSkeleton />}

        {error && !loading && (
          <ErrorState message={error} onRetry={fetchReport} />
        )}

        {report && !loading && (
          <div className="animate-neuro-fade-in">
            {/* Tab: Report Card */}
            {activeTab === "report" && (
              <div className="mx-auto max-w-2xl">
                <ReportCard
                  scores={report.scores}
                  darkPatterns={report.dark_patterns}
                  summaries={report.template_summaries}
                  metadata={report.metadata}
                />
              </div>
            )}

            {/* Tab: Brain Heatmap */}
            {activeTab === "brain" && (
              <div className="h-[calc(100vh-12rem)] min-h-[560px]">
                {webglAvailable ? (
                  <BrainHeatmap
                    meshUrl="/api/mesh"
                    activationUrl={activationUrl}
                    activationMeta={report.vertex_activation}
                    atlas={atlas}
                    regionBreakdown={report.scores.region_breakdown}
                    timeLabels={timeLabels}
                    colormap={colormap}
                    onUnavailable={() => setWebglAvailable(false)}
                  />
                ) : (
                  <BrainHeatmapFallback
                    projectionPaths={report.projection_paths}
                    jobId={jobId}
                    reason="hardware-accelerated WebGL is unavailable in this browser"
                  />
                )}
              </div>
            )}

            {/* Tab: Website Overlay */}
            {activeTab === "overlay" && (
              <div className="h-[calc(100vh-12rem)] min-h-[560px]">
                <WebsiteOverlay
                  screenshotUrl={screenshotUrl}
                  overlay={report.overlay}
                  darkPatterns={report.dark_patterns.patterns}
                  viewportWidth={report.metadata.viewport_w || 1440}
                />
              </div>
            )}

            {/* Tab: Scroll Timeline */}
            {activeTab === "timeline" && (
              <div className="h-[calc(100vh-12rem)] min-h-[560px]">
                <ScrollTimeline
                  timeline={report.timeline}
                  darkPatterns={report.dark_patterns.patterns}
                  viewportHeight={report.metadata.viewport_h || 900}
                />
              </div>
            )}
          </div>
        )}
      </main>

      {/* Chatbot panel */}
      {llmAvailable && report && (
        <ChatbotPanel
          jobId={jobId}
          report={report}
          isOpen={chatOpen}
          onClose={() => setChatOpen(false)}
          provider={health?.llm_provider ?? "LLM"}
        />
      )}
    </div>
  );
}
