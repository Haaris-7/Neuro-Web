"use client";

import { useState } from "react";
import { jobFileUrl } from "@/lib/types";

interface BrainHeatmapFallbackProps {
  projectionPaths: Record<string, string>;
  jobId: string;
  reason?: string;
}

const VIEW_ORDER = [
  { key: "lateral_left", label: "Left lateral" },
  { key: "medial_left", label: "Left medial" },
  { key: "lateral_right", label: "Right lateral" },
  { key: "medial_right", label: "Right medial" },
  { key: "dorsal", label: "Dorsal" },
];

export function BrainHeatmapFallback({
  projectionPaths,
  jobId,
  reason = "WebGL is unavailable in this browser",
}: BrainHeatmapFallbackProps) {
  const available = VIEW_ORDER.filter((v) => projectionPaths[v.key]);
  const [selected, setSelected] = useState(available[0]?.key ?? "");

  if (available.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800/40 bg-slate-900/30">
        <p className="text-sm text-slate-500">
          No brain projections were rendered for this analysis and {reason.toLowerCase()}.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap gap-1 rounded-xl bg-slate-900/60 p-1">
        {available.map((v) => (
          <button
            key={v.key}
            onClick={() => setSelected(v.key)}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              selected === v.key
                ? "bg-slate-700/80 text-slate-100 shadow-sm"
                : "text-slate-500 hover:text-slate-300"
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14] p-4">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={jobFileUrl(jobId, projectionPaths[selected])}
          alt={`Brain activation, ${selected.replace("_", " ")} view`}
          className="mx-auto max-h-[520px] object-contain"
        />
      </div>

      <p className="text-center text-[10px] text-slate-600">
        Static projections rendered on the server ({reason}).
      </p>
    </div>
  );
}
