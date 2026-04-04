"use client";

import { useMemo, useState } from "react";
import {
  TransformWrapper,
  TransformComponent,
} from "react-zoom-pan-pinch";
import type { ElementOverlay, DarkPatternMatch } from "@/lib/types";

interface WebsiteOverlayProps {
  screenshotUrl: string;
  overlay: ElementOverlay[];
  darkPatterns: DarkPatternMatch[];
  viewportWidth?: number;
}

function intensityToColor(
  intensity: number,
  attentionRatio: number,
): string {
  const hue = attentionRatio > 0.6 ? 190 : attentionRatio < 0.4 ? 270 : 220;
  const lightness = 50 + (1 - intensity) * 20;
  return `hsla(${hue}, 80%, ${lightness}%, 0.45)`;
}

function OverlayRegion({
  el,
  scale,
}: {
  el: ElementOverlay;
  scale: number;
}) {
  const [hovered, setHovered] = useState(false);
  const total = el.attention_contrib + el.emotion_contrib || 1;
  const attRatio = el.attention_contrib / total;
  const color = intensityToColor(el.intensity, attRatio);

  return (
    <div
      className="absolute border transition-opacity"
      style={{
        left: el.bbox.x * scale,
        top: el.bbox.y * scale,
        width: el.bbox.width * scale,
        height: el.bbox.height * scale,
        background: color,
        borderColor: hovered
          ? "rgb(34 211 238 / 0.8)"
          : "rgb(34 211 238 / 0.15)",
        mixBlendMode: "multiply",
        zIndex: hovered ? 10 : 1,
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {hovered && (
        <div
          className="pointer-events-none absolute -top-20 left-1/2 z-50 -translate-x-1/2 whitespace-nowrap rounded-lg border border-slate-700/80 bg-[#0a0e1a]/95 px-3 py-2 shadow-xl backdrop-blur-sm"
        >
          <p className="text-[10px] font-medium text-slate-300">
            &lt;{el.tag}&gt;
          </p>
          <div className="mt-1 flex gap-3 text-[10px]">
            <span className="text-cyan-400">
              Att: {(el.attention_contrib * 10).toFixed(1)}
            </span>
            <span className="text-violet-400">
              Emo: {(el.emotion_contrib * 10).toFixed(1)}
            </span>
            <span className="text-slate-400">
              Int: {(el.intensity * 10).toFixed(1)}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function DarkPatternBadge({
  dp,
  scale,
}: {
  dp: DarkPatternMatch;
  scale: number;
}) {
  if (!dp.bbox) return null;

  return (
    <div
      className="absolute z-20 flex items-center gap-1 rounded-full border border-red-500/40 bg-red-950/80 px-2 py-0.5 text-[10px] font-semibold text-red-300 backdrop-blur-sm"
      style={{
        left: dp.bbox.x * scale,
        top: (dp.bbox.y + dp.bbox.scroll_y) * scale - 24,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
      {dp.pattern_type.replace("_", " ")}
    </div>
  );
}

export function WebsiteOverlay({
  screenshotUrl,
  overlay,
  darkPatterns,
  viewportWidth = 1440,
}: WebsiteOverlayProps) {
  const [opacity, setOpacity] = useState(0.6);
  const [blendMode, setBlendMode] = useState<"multiply" | "screen" | "normal">(
    "multiply",
  );
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgDimensions, setImgDimensions] = useState({ w: 0, h: 0 });

  const scale = useMemo(() => {
    if (!imgDimensions.w) return 1;
    return imgDimensions.w / viewportWidth;
  }, [imgDimensions.w, viewportWidth]);

  const dpWithBbox = useMemo(
    () => darkPatterns.filter((dp) => dp.bbox),
    [darkPatterns],
  );

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex items-center gap-2">
          <label className="text-[10px] font-medium uppercase tracking-widest text-slate-500">
            Opacity
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-400"
          />
          <span className="w-8 text-right font-mono text-[10px] text-slate-500">
            {Math.round(opacity * 100)}%
          </span>
        </div>
        <div className="flex gap-1 rounded-lg bg-slate-900/60 p-0.5">
          {(["multiply", "screen", "normal"] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setBlendMode(mode)}
              className={`rounded-md px-2 py-1 text-[10px] font-medium transition ${
                blendMode === mode
                  ? "bg-slate-700/80 text-slate-200"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Screenshot + overlay */}
      <div className="relative flex-1 overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14]">
        <TransformWrapper
          initialScale={0.5}
          minScale={0.2}
          maxScale={3}
          centerOnInit
        >
          <TransformComponent
            wrapperStyle={{ width: "100%", height: "100%" }}
            contentStyle={{ position: "relative" }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={screenshotUrl}
              alt="Website screenshot"
              onLoad={(e) => {
                const img = e.currentTarget;
                setImgDimensions({ w: img.naturalWidth, h: img.naturalHeight });
                setImgLoaded(true);
              }}
              className="block max-w-none"
              draggable={false}
            />

            {imgLoaded && (
              <div
                className="absolute inset-0"
                style={{ opacity, mixBlendMode: blendMode }}
              >
                {overlay.map((el, i) => (
                  <OverlayRegion key={i} el={el} scale={scale} />
                ))}
              </div>
            )}

            {imgLoaded &&
              dpWithBbox.map((dp, i) => (
                <DarkPatternBadge key={i} dp={dp} scale={scale} />
              ))}
          </TransformComponent>
        </TransformWrapper>

        <div className="pointer-events-none absolute right-4 top-4 text-[10px] text-slate-600">
          Scroll to zoom · Drag to pan
        </div>
      </div>
    </div>
  );
}
