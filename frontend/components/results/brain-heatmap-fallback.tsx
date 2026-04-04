"use client";

import { useState } from "react";
import { ColorLegend } from "./color-legend";
import type { ColormapName } from "@/lib/colormaps";

interface BrainHeatmapFallbackProps {
  projectionPaths: Record<string, string>;
  jobId: string;
  colormap?: ColormapName;
}

const VIEW_ORDER = [
  { key: "lateral_left", label: "Left Lateral" },
  { key: "medial_left", label: "Left Medial" },
  { key: "lateral_right", label: "Right Lateral" },
  { key: "medial_right", label: "Right Medial" },
  { key: "dorsal", label: "Dorsal" },
];

export function BrainHeatmapFallback({
  projectionPaths,
  jobId,
  colormap = "viridis",
}: BrainHeatmapFallbackProps) {
  const available = VIEW_ORDER.filter((v) => projectionPaths[v.key]);
  const [selected, setSelected] = useState(available[0]?.key || "");

  if (available.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-2xl border border-slate-800/40 bg-slate-900/30">
        <p className="text-sm text-slate-500">
          No brain projections available. WebGL is required for the interactive 3D view.
        </p>
      </div>
    );
  }

  const filename = projectionPaths[selected];
  const basename = filename?.split("/").pop() || "";
  const src = `/api/jobs/${jobId}/files/${basename}`;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex gap-1 rounded-xl bg-slate-900/60 p-1">
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

      <div className="relative overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14]">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={src}
          alt={`Brain activation - ${selected}`}
          className="mx-auto max-h-[500px] object-contain"
        />
        <div className="absolute bottom-4 left-4 right-4">
          <ColorLegend colormap={colormap} min={0} max={10} />
        </div>
      </div>

      <p className="text-center text-[10px] text-slate-600">
        2D orthographic projections (WebGL unavailable)
      </p>
    </div>
  );
}
