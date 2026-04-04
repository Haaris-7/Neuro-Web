"use client";

import { useMemo } from "react";
import { getColormapGradientStops, type ColormapName } from "@/lib/colormaps";

interface ColorLegendProps {
  colormap?: ColormapName;
  min?: number;
  max?: number;
  label?: string;
  className?: string;
}

export function ColorLegend({
  colormap = "viridis",
  min = 0,
  max = 10,
  label = "Activation Intensity",
  className = "",
}: ColorLegendProps) {
  const gradient = useMemo(() => {
    const stops = getColormapGradientStops(colormap, 12);
    return `linear-gradient(to right, ${stops.join(", ")})`;
  }, [colormap]);

  const ticks = useMemo(() => {
    const count = 5;
    return Array.from({ length: count }, (_, i) => {
      const val = min + (max - min) * (i / (count - 1));
      return { pct: (i / (count - 1)) * 100, label: val.toFixed(1) };
    });
  }, [min, max]);

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
        {label}
      </span>
      <div
        className="h-2.5 w-full rounded-full"
        style={{ background: gradient }}
      />
      <div className="relative flex justify-between">
        {ticks.map((t) => (
          <span
            key={t.pct}
            className="text-[10px] font-mono text-slate-600"
          >
            {t.label}
          </span>
        ))}
      </div>
    </div>
  );
}
