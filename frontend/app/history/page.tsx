"use client";

import Link from "next/link";
import { AnalysisHistory } from "@/components/analysis-history";

export default function HistoryPage() {
  return (
    <div className="relative min-h-screen bg-[#0a0e1a] text-slate-100">
      <div
        className="pointer-events-none fixed inset-0 bg-[radial-gradient(ellipse_60%_30%_at_50%_0%,rgb(59_130_246_/_0.08),transparent)]"
        aria-hidden
      />
      <div className="pointer-events-none fixed inset-0 noise-overlay" aria-hidden />

      <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-[#0a0e1a]/90 backdrop-blur-lg">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="text-sm font-medium text-slate-500 transition hover:text-cyan-300"
            >
              ← Home
            </Link>
            <span className="h-4 w-px bg-slate-800" />
            <h1 className="text-sm font-semibold text-slate-300">
              Analysis History
            </h1>
          </div>
          <Link
            href="/"
            className="rounded-lg bg-gradient-to-r from-cyan-500 to-violet-600 px-4 py-1.5 text-xs font-semibold text-white transition hover:brightness-110"
          >
            New analysis
          </Link>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-3xl px-6 py-8">
        <AnalysisHistory />
      </main>
    </div>
  );
}
