"use client";

import { useMemo, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ReferenceDot,
} from "recharts";
import type { TimelineData, DarkPatternMatch } from "@/lib/types";

interface ScrollTimelineProps {
  timeline: TimelineData;
  darkPatterns: DarkPatternMatch[];
  viewportHeight: number;
}

type SeriesKey = "overall" | "attention" | "emotion";

const SERIES_CONFIG: {
  key: SeriesKey;
  dataKey: string;
  label: string;
  color: string;
}[] = [
  { key: "overall", dataKey: "overall_intensity", label: "Overall", color: "#e2e8f0" },
  { key: "attention", dataKey: "attention_intensity", label: "Attention", color: "#22d3ee" },
  { key: "emotion", dataKey: "emotion_intensity", label: "Emotion", color: "#8b5cf6" },
];

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ dataKey: string; value: number; color: string }>;
  label?: number;
}) {
  if (!active || !payload?.length) return null;

  return (
    <div className="rounded-lg border border-slate-700/80 bg-[#0a0e1a]/95 px-3 py-2 shadow-xl backdrop-blur-sm">
      <p className="mb-1.5 text-[10px] font-medium text-slate-400">
        {typeof label === "number" ? `${label.toFixed(1)}s` : label}
      </p>
      {payload.map((entry) => (
        <div
          key={entry.dataKey}
          className="flex items-center gap-2 text-[11px]"
        >
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: entry.color }}
          />
          <span className="text-slate-400">
            {SERIES_CONFIG.find((s) => s.dataKey === entry.dataKey)?.label ||
              entry.dataKey}
            :
          </span>
          <span className="font-mono font-medium" style={{ color: entry.color }}>
            {entry.value.toFixed(1)}
          </span>
        </div>
      ))}
    </div>
  );
}

export function ScrollTimeline({
  timeline,
  darkPatterns,
  viewportHeight,
}: ScrollTimelineProps) {
  const [activeSeries, setActiveSeries] = useState<Set<SeriesKey>>(
    new Set(["overall", "attention", "emotion"]),
  );

  const data = useMemo(
    () =>
      timeline.series.map((pt) => ({
        time_s: pt.time_s,
        overall_intensity: pt.overall_intensity,
        attention_intensity: pt.attention_intensity,
        emotion_intensity: pt.emotion_intensity,
        scroll_px: pt.scroll_position_px,
      })),
    [timeline.series],
  );

  const dpMarkers = useMemo(() => {
    if (timeline.series.length === 0) return [];
    const markers = darkPatterns.flatMap((dp) => {
      if (!dp.bbox) return [];
      const elementY = dp.bbox.y;
      const first = timeline.series.find(
        (pt) => elementY < pt.scroll_position_px + viewportHeight && elementY + dp.bbox!.height > pt.scroll_position_px,
      );
      return first ? [{ dp, time_s: first.time_s }] : [];
    });
    const seen = new Set<string>();
    return markers.filter((m) => {
      const key = `${m.dp.pattern_type}@${m.time_s.toFixed(1)}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [darkPatterns, timeline.series, viewportHeight]);

  const toggleSeries = (key: SeriesKey) => {
    setActiveSeries((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        if (next.size > 1) next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Series toggles */}
      <div className="flex flex-wrap items-center gap-3">
        {SERIES_CONFIG.map((s) => (
          <button
            key={s.key}
            onClick={() => toggleSeries(s.key)}
            className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              activeSeries.has(s.key)
                ? "bg-slate-800/80 text-slate-200"
                : "text-slate-600 hover:text-slate-400"
            }`}
          >
            <span
              className="h-2 w-2 rounded-full"
              style={{
                background: activeSeries.has(s.key)
                  ? s.color
                  : "rgb(51 65 85 / 0.5)",
              }}
            />
            {s.label}
          </button>
        ))}
        <span className="text-[10px] text-slate-600">
          {timeline.series.length} timesteps · {timeline.duration_s.toFixed(1)}s · scores 0–10
        </span>
      </div>

      {/* Chart */}
      <div className="flex-1 rounded-2xl border border-slate-800/40 bg-[#060a14] p-4">
        <ResponsiveContainer width="100%" height="100%" minHeight={300}>
          <LineChart
            data={data}
            margin={{ top: 20, right: 20, bottom: 20, left: 10 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgb(30 41 59 / 0.3)"
            />
            <XAxis
              dataKey="time_s"
              type="number"
              domain={["dataMin", "dataMax"]}
              tickFormatter={(v: number) => `${v.toFixed(0)}s`}
              tick={{ fill: "#475569", fontSize: 10 }}
              axisLine={{ stroke: "#1e293b" }}
              tickLine={{ stroke: "#1e293b" }}
            />
            <YAxis
              domain={[0, 10]}
              tick={{ fill: "#475569", fontSize: 10 }}
              axisLine={{ stroke: "#1e293b" }}
              tickLine={{ stroke: "#1e293b" }}
              width={35}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{ stroke: "rgb(34 211 238 / 0.2)" }}
            />

            {SERIES_CONFIG.map(
              (s) =>
                activeSeries.has(s.key) && (
                  <Line
                    key={s.key}
                    type="monotone"
                    dataKey={s.dataKey}
                    stroke={s.color}
                    strokeWidth={s.key === "overall" ? 2 : 1.5}
                    dot={false}
                    activeDot={{
                      r: 4,
                      fill: s.color,
                      stroke: "#0a0e1a",
                      strokeWidth: 2,
                    }}
                    opacity={s.key === "overall" ? 1 : 0.8}
                  />
                ),
            )}

            {/* Peak annotations */}
            {timeline.peaks.map((peak, i) => (
              <ReferenceDot
                key={`peak-${i}`}
                x={peak.time_s}
                y={peak.intensity}
                r={5}
                fill="#fbbf24"
                stroke="#0a0e1a"
                strokeWidth={2}
              />
            ))}

            {/* Dark pattern markers */}
            {dpMarkers.map((marker, i) => (
              <ReferenceLine
                key={`dp-${i}`}
                x={marker.time_s}
                stroke="#ef4444"
                strokeDasharray="4 4"
                strokeWidth={1}
                opacity={0.6}
                label={{
                  value: marker.dp.pattern_type.replace("_", " "),
                  position: "top",
                  fill: "#ef4444",
                  fontSize: 9,
                }}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Peaks list */}
      {timeline.peaks.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-400">
            Peak Activations
          </h4>
          <div className="flex flex-wrap gap-2">
            {timeline.peaks.map((peak, i) => (
              <div
                key={i}
                className="flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-1.5"
              >
                <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
                <span className="text-[10px] text-slate-400">
                  {peak.time_s.toFixed(1)}s
                </span>
                <span className="font-mono text-[10px] font-semibold text-amber-300">
                  {peak.intensity.toFixed(1)}
                </span>
                <span className="text-[10px] text-slate-500">{peak.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
