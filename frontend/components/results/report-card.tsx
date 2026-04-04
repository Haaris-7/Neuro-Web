"use client";

import { useMemo } from "react";
import type {
  ScoreReport,
  DarkPatternReport,
  TemplateSummaries,
  DarkPatternType,
} from "@/lib/types";

interface ReportCardProps {
  scores: ScoreReport;
  darkPatterns: DarkPatternReport;
  summaries: TemplateSummaries;
  url: string;
  captureDate: string;
  hasEnhancedReport?: boolean;
}

const GAUGE_RADIUS = 54;
const GAUGE_STROKE = 7;
const GAUGE_CIRCUMFERENCE = 2 * Math.PI * GAUGE_RADIUS;

function CircularGauge({
  value,
  max = 10,
  label,
  color,
  size = "lg",
  delay = 0,
}: {
  value: number;
  max?: number;
  label: string;
  color: string;
  size?: "lg" | "sm";
  delay?: number;
}) {
  const pct = Math.min(value / max, 1);
  const r = size === "lg" ? GAUGE_RADIUS : 38;
  const stroke = size === "lg" ? GAUGE_STROKE : 5;
  const circ = 2 * Math.PI * r;
  const dim = (r + stroke) * 2;

  return (
    <div className="flex flex-col items-center">
      <div className="relative" style={{ width: dim, height: dim }}>
        <svg
          width={dim}
          height={dim}
          className="-rotate-90"
          viewBox={`0 0 ${dim} ${dim}`}
        >
          <circle
            cx={r + stroke}
            cy={r + stroke}
            r={r}
            fill="none"
            stroke="rgb(30 41 59 / 0.6)"
            strokeWidth={stroke}
          />
          <circle
            cx={r + stroke}
            cy={r + stroke}
            r={r}
            fill="none"
            stroke={`url(#gauge-grad-${label.replace(/\s/g, "")})`}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circ}
            strokeDashoffset={circ}
            className="animate-gauge-fill"
            style={
              {
                "--gauge-circumference": circ,
                "--gauge-offset": circ * (1 - pct),
                animationDelay: `${delay}ms`,
              } as React.CSSProperties
            }
          />
          <defs>
            <linearGradient
              id={`gauge-grad-${label.replace(/\s/g, "")}`}
              x1="0"
              y1="0"
              x2="1"
              y2="1"
            >
              <stop offset="0%" stopColor={color} />
              <stop offset="100%" stopColor={color} stopOpacity={0.5} />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span
            className="animate-score-count font-mono font-bold tracking-tight"
            style={{
              fontSize: size === "lg" ? "2rem" : "1.35rem",
              color,
              animationDelay: `${delay + 400}ms`,
            }}
          >
            {value.toFixed(1)}
          </span>
          {size === "lg" && (
            <span className="mt-0.5 text-[10px] font-medium uppercase tracking-widest text-slate-500">
              / {max}
            </span>
          )}
        </div>
      </div>
      <p
        className="mt-2 text-center text-xs font-semibold uppercase tracking-[0.15em]"
        style={{ color: `color-mix(in srgb, ${color} 70%, white)` }}
      >
        {label}
      </p>
    </div>
  );
}

function PillarBar({
  value,
  max = 10,
  label,
  color,
  description,
  delay = 0,
}: {
  value: number;
  max?: number;
  label: string;
  color: string;
  description: string;
  delay?: number;
}) {
  const pct = Math.min(value / max, 1) * 100;

  return (
    <div
      className="animate-stagger-fade rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5"
      style={{ animationDelay: `${delay}ms` }}
    >
      <div className="mb-3 flex items-baseline justify-between">
        <h4 className="text-sm font-semibold text-slate-200">{label}</h4>
        <span
          className="font-mono text-lg font-bold"
          style={{ color }}
        >
          {value.toFixed(1)}
        </span>
      </div>
      <div className="mb-3 h-2 overflow-hidden rounded-full bg-slate-800/80">
        <div
          className="h-full rounded-full transition-all duration-1000 ease-out"
          style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg, ${color}, color-mix(in srgb, ${color} 60%, transparent))`,
            boxShadow: `0 0 12px ${color}40`,
            transitionDelay: `${delay}ms`,
          }}
        />
      </div>
      <p className="text-xs leading-relaxed text-slate-500">{description}</p>
    </div>
  );
}

const DARK_PATTERN_META: Record<
  DarkPatternType,
  { label: string; icon: string; color: string }
> = {
  urgency: { label: "Urgency", icon: "⏱", color: "#f97316" },
  confirmshaming: { label: "Confirmshaming", icon: "😔", color: "#ec4899" },
  pre_checked: { label: "Pre-checked", icon: "☑", color: "#a855f7" },
  hidden_costs: { label: "Hidden Costs", icon: "$", color: "#ef4444" },
  misdirection: { label: "Misdirection", icon: "↗", color: "#f59e0b" },
  forced_continuity: {
    label: "Forced Continuity",
    icon: "🔄",
    color: "#6366f1",
  },
};

export function ReportCard({
  scores,
  darkPatterns,
  summaries,
  url,
  captureDate,
  hasEnhancedReport,
}: ReportCardProps) {
  const hostname = useMemo(() => {
    try {
      return new URL(url).hostname;
    } catch {
      return url;
    }
  }, [url]);

  const dateStr = useMemo(() => {
    try {
      return new Date(captureDate).toLocaleDateString("en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return captureDate;
    }
  }, [captureDate]);

  return (
    <div className="space-y-8">
      {/* Hero score */}
      <div className="flex flex-col items-center py-4">
        <div className="relative">
          <div
            className="absolute inset-0 rounded-full opacity-30 blur-2xl"
            style={{
              background: `radial-gradient(circle, ${
                scores.impact_score >= 7
                  ? "#ef4444"
                  : scores.impact_score >= 4
                    ? "#f59e0b"
                    : "#22d3ee"
              } 0%, transparent 70%)`,
            }}
          />
          <CircularGauge
            value={scores.impact_score}
            label="Brain Impact"
            color={
              scores.impact_score >= 7
                ? "#ef4444"
                : scores.impact_score >= 4
                  ? "#f59e0b"
                  : "#22d3ee"
            }
            size="lg"
          />
        </div>
        <p className="mt-4 max-w-md text-center text-sm leading-relaxed text-slate-400">
          {summaries.overall}
        </p>
        <div className="mt-3 flex items-center gap-3 text-xs text-slate-600">
          <span>{hostname}</span>
          <span className="h-1 w-1 rounded-full bg-slate-700" />
          <span>{dateStr}</span>
          {hasEnhancedReport && (
            <>
              <span className="h-1 w-1 rounded-full bg-slate-700" />
              <span className="rounded-full border border-violet-500/30 bg-violet-500/10 px-2 py-0.5 text-violet-400">
                AI-enhanced
              </span>
            </>
          )}
        </div>
      </div>

      {/* Pillar scores */}
      <div className="grid gap-4 sm:grid-cols-2">
        <PillarBar
          value={scores.attention_score}
          label="Attention Capture"
          color="#22d3ee"
          description={summaries.attention}
          delay={200}
        />
        <PillarBar
          value={scores.emotion_score}
          label="Emotional Trigger"
          color="#8b5cf6"
          description={summaries.emotion}
          delay={350}
        />
      </div>

      {/* Secondary gauges row */}
      <div className="flex items-center justify-center gap-10 rounded-2xl border border-slate-800/40 bg-slate-900/20 py-6">
        <CircularGauge
          value={scores.attention_score}
          label="Attention"
          color="#22d3ee"
          size="sm"
          delay={400}
        />
        <CircularGauge
          value={scores.emotion_score}
          label="Emotion"
          color="#8b5cf6"
          size="sm"
          delay={550}
        />
        <CircularGauge
          value={scores.temporal_variance}
          label="Variance"
          color="#3b82f6"
          size="sm"
          delay={700}
        />
      </div>

      {/* Temporal dynamics */}
      <div
        className="animate-stagger-fade rounded-2xl border border-slate-800/60 bg-slate-900/40 p-5"
        style={{ animationDelay: "500ms" }}
      >
        <h3 className="mb-2 text-sm font-semibold text-slate-200">
          Temporal Dynamics
        </h3>
        <p className="text-xs leading-relaxed text-slate-500">
          {summaries.temporal_dynamics}
        </p>
      </div>

      {/* Dark patterns */}
      {darkPatterns.patterns.length > 0 && (
        <div
          className="animate-stagger-fade space-y-4"
          style={{ animationDelay: "600ms" }}
        >
          <div className="flex items-center gap-3">
            <h3 className="text-sm font-semibold text-slate-200">
              Dark Patterns Detected
            </h3>
            <span className="rounded-full bg-red-500/15 px-2.5 py-0.5 text-xs font-semibold text-red-400">
              {darkPatterns.patterns.length} found
            </span>
          </div>
          <p className="text-xs leading-relaxed text-slate-500">
            {summaries.dark_patterns}
          </p>
          <div className="space-y-2">
            {darkPatterns.patterns.map((dp, i) => {
              const meta = DARK_PATTERN_META[dp.pattern_type] || {
                label: dp.pattern_type,
                icon: "⚠",
                color: "#f59e0b",
              };
              return (
                <div
                  key={`${dp.pattern_type}-${i}`}
                  className="group flex gap-3 rounded-xl border border-slate-800/50 bg-slate-900/30 px-4 py-3 transition hover:border-slate-700/60"
                >
                  <span
                    className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-sm"
                    style={{
                      background: `${meta.color}15`,
                      border: `1px solid ${meta.color}30`,
                    }}
                  >
                    {meta.icon}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className="text-xs font-semibold"
                        style={{ color: meta.color }}
                      >
                        {meta.label}
                      </span>
                      <span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                        {Math.round(dp.confidence * 100)}% confidence
                      </span>
                    </div>
                    <p className="mt-1 truncate text-xs text-slate-500 group-hover:whitespace-normal">
                      {dp.evidence_text}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {darkPatterns.patterns.length === 0 && (
        <div
          className="animate-stagger-fade rounded-2xl border border-emerald-500/10 bg-emerald-500/5 p-5"
          style={{ animationDelay: "600ms" }}
        >
          <div className="flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-500/10 text-sm text-emerald-400">
              ✓
            </span>
            <div>
              <h3 className="text-sm font-semibold text-emerald-300">
                No Dark Patterns Detected
              </h3>
              <p className="mt-0.5 text-xs text-slate-500">
                {summaries.dark_patterns}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Region breakdown */}
      {scores.region_breakdown.length > 0 && (
        <div
          className="animate-stagger-fade"
          style={{ animationDelay: "700ms" }}
        >
          <h3 className="mb-4 text-sm font-semibold text-slate-200">
            Brain Region Activity
          </h3>
          <div className="space-y-2">
            {scores.region_breakdown
              .sort((a, b) => b.normalized_score - a.normalized_score)
              .slice(0, 8)
              .map((region) => {
                const groupColors: Record<string, string> = {
                  visual: "#22d3ee",
                  attention: "#3b82f6",
                  emotional: "#8b5cf6",
                  language: "#34d399",
                  default_mode: "#64748b",
                };
                const color =
                  groupColors[region.functional_group] || "#64748b";
                const pct =
                  Math.min(region.normalized_score / 10, 1) * 100;

                return (
                  <div
                    key={region.region_name}
                    className="group flex items-center gap-3"
                  >
                    <span
                      className="w-20 truncate text-right text-[11px] font-medium text-slate-500 group-hover:text-slate-400"
                      title={region.region_name}
                    >
                      {region.region_name}
                    </span>
                    <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-slate-800/60">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${pct}%`,
                          background: color,
                          opacity: 0.8,
                        }}
                      />
                    </div>
                    <span
                      className="w-8 text-right font-mono text-[11px]"
                      style={{ color }}
                    >
                      {region.normalized_score.toFixed(1)}
                    </span>
                  </div>
                );
              })}
          </div>
        </div>
      )}

      {/* Disclaimer */}
      <div className="rounded-xl border border-slate-800/40 bg-slate-900/20 px-4 py-3">
        <p className="text-[10px] leading-relaxed text-slate-600">
          <strong className="text-slate-500">Scientific disclaimer:</strong>{" "}
          Brain activation predictions are generated by Meta&apos;s TRIBE v2 model
          and represent statistical approximations, not direct measurements.
          Scores are relative and should not be interpreted as clinical
          assessments. Powered by TRIBE v2 on fsaverage5 cortical mesh.
        </p>
      </div>
    </div>
  );
}
