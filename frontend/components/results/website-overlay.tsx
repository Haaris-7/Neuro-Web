"use client";

import { useMemo, useState } from "react";
import { TransformComponent, TransformWrapper } from "react-zoom-pan-pinch";
import type { DarkPatternMatch, ElementOverlay } from "@/lib/types";

interface WebsiteOverlayProps {
  screenshotUrl: string;
  overlay: ElementOverlay[];
  darkPatterns: DarkPatternMatch[];
  viewportWidth: number;
}

type Channel = "overall" | "attention" | "emotion";

const CHANNELS: { key: Channel; label: string; hue: number }[] = [
  { key: "overall", label: "Overall", hue: 200 },
  { key: "attention", label: "Attention", hue: 190 },
  { key: "emotion", label: "Emotion", hue: 270 },
];

function channelValue(el: ElementOverlay, channel: Channel): number {
  if (channel === "attention") return el.attention_contrib;
  if (channel === "emotion") return el.emotion_contrib;
  return el.intensity;
}

function OverlayRegion({
  el,
  scale,
  channel,
  hue,
  hovered,
  onHover,
}: {
  el: ElementOverlay;
  scale: number;
  channel: Channel;
  hue: number;
  hovered: boolean;
  onHover: (el: ElementOverlay | null) => void;
}) {
  const value = channelValue(el, channel);
  const alpha = 0.15 + value * 0.55;
  return (
    <div
      className="absolute border transition-colors"
      style={{
        left: el.bbox.x * scale,
        top: el.bbox.y * scale,
        width: el.bbox.width * scale,
        height: el.bbox.height * scale,
        background: `hsla(${hue}, 85%, ${40 + value * 25}%, ${alpha})`,
        borderColor: hovered ? "rgb(34 211 238 / 0.9)" : "rgb(34 211 238 / 0.12)",
        zIndex: hovered ? 10 : 1,
      }}
      onMouseEnter={() => onHover(el)}
      onMouseLeave={() => onHover(null)}
    />
  );
}

function HoverPanel({ el }: { el: ElementOverlay }) {
  return (
    <div className="pointer-events-none absolute bottom-4 left-4 z-30 rounded-lg border border-slate-700/80 bg-[#0a0e1a]/95 px-3 py-2 shadow-xl backdrop-blur-sm">
      <p className="text-[10px] font-medium text-slate-300">
        &lt;{el.tag}&gt; · {Math.round(el.bbox.width)}×{Math.round(el.bbox.height)} px ·{" "}
        {el.fixed
          ? "fixed, always on screen"
          : `on screen for ${el.visible_timesteps.length} timestep${el.visible_timesteps.length === 1 ? "" : "s"}`}
      </p>
      <div className="mt-1 flex gap-3 font-mono text-[10px]">
        <span className="text-slate-300">Overall {(el.intensity * 10).toFixed(1)}</span>
        <span className="text-cyan-400">Attention {(el.attention_contrib * 10).toFixed(1)}</span>
        <span className="text-violet-400">Emotion {(el.emotion_contrib * 10).toFixed(1)}</span>
      </div>
    </div>
  );
}

function DarkPatternBadge({ dp, scale }: { dp: DarkPatternMatch; scale: number }) {
  if (!dp.bbox) return null;
  return (
    <div
      className="absolute z-20"
      style={{
        left: dp.bbox.x * scale,
        top: dp.bbox.y * scale,
        width: Math.max(dp.bbox.width * scale, 12),
        height: Math.max(dp.bbox.height * scale, 12),
      }}
      title={dp.evidence_text}
    >
      <div className="absolute inset-0 rounded border-2 border-red-500/70 bg-red-500/10" />
      <span className="absolute -top-5 left-0 flex items-center gap-1 whitespace-nowrap rounded-full border border-red-500/40 bg-red-950/90 px-2 py-0.5 text-[10px] font-semibold text-red-200 backdrop-blur-sm">
        <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
        {dp.pattern_type.replace("_", " ")}
      </span>
    </div>
  );
}

export function WebsiteOverlay({
  screenshotUrl,
  overlay,
  darkPatterns,
  viewportWidth,
}: WebsiteOverlayProps) {
  const [opacity, setOpacity] = useState(0.75);
  const [channel, setChannel] = useState<Channel>("overall");
  const [showDarkPatterns, setShowDarkPatterns] = useState(true);
  const [imgWidth, setImgWidth] = useState(0);
  const [imgError, setImgError] = useState(false);
  const [hovered, setHovered] = useState<ElementOverlay | null>(null);

  const scale = imgWidth ? imgWidth / viewportWidth : 1;
  const hue = CHANNELS.find((c) => c.key === channel)?.hue ?? 200;
  const anchored = useMemo(() => darkPatterns.filter((dp) => dp.bbox), [darkPatterns]);
  const regionsLargestFirst = useMemo(
    () =>
      [...overlay].sort(
        (a, b) => b.bbox.width * b.bbox.height - a.bbox.width * a.bbox.height,
      ),
    [overlay],
  );

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4">
        <div className="flex gap-1 rounded-lg bg-slate-900/60 p-0.5">
          {CHANNELS.map((c) => (
            <button
              key={c.key}
              onClick={() => setChannel(c.key)}
              className={`rounded-md px-2.5 py-1 text-[11px] font-medium transition ${
                channel === c.key
                  ? "bg-slate-700/80 text-slate-200"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>
        <label className="flex items-center gap-2 text-[10px] font-medium uppercase tracking-widest text-slate-500">
          Opacity
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={opacity}
            onChange={(e) => setOpacity(parseFloat(e.target.value))}
            className="h-1.5 w-24 cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-400"
          />
          <span className="w-8 text-right font-mono normal-case tracking-normal text-slate-500">
            {Math.round(opacity * 100)}%
          </span>
        </label>
        <label className="flex items-center gap-2 text-[11px] text-slate-400">
          <input
            type="checkbox"
            checked={showDarkPatterns}
            onChange={(e) => setShowDarkPatterns(e.target.checked)}
            className="accent-red-500"
          />
          Dark patterns ({anchored.length} located)
        </label>
        <span className="text-[10px] text-slate-600">{overlay.length} regions</span>
      </div>

      <div className="relative flex-1 overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14]">
        {imgError ? (
          <div className="flex h-full items-center justify-center text-sm text-slate-500">
            Screenshot unavailable for this analysis.
          </div>
        ) : (
          <TransformWrapper initialScale={0.5} minScale={0.15} maxScale={3} centerOnInit>
            <TransformComponent
              wrapperStyle={{ width: "100%", height: "100%" }}
              contentStyle={{ position: "relative" }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={screenshotUrl}
                alt="Website screenshot"
                onLoad={(e) => setImgWidth(e.currentTarget.naturalWidth)}
                onError={() => setImgError(true)}
                className="block max-w-none"
                draggable={false}
              />
              {imgWidth > 0 && (
                <div className="absolute inset-0" style={{ opacity }}>
                  {regionsLargestFirst.map((el, i) => (
                    <OverlayRegion
                      key={i}
                      el={el}
                      scale={scale}
                      channel={channel}
                      hue={hue}
                      hovered={hovered === el}
                      onHover={setHovered}
                    />
                  ))}
                </div>
              )}
              {imgWidth > 0 &&
                showDarkPatterns &&
                anchored.map((dp, i) => <DarkPatternBadge key={i} dp={dp} scale={scale} />)}
            </TransformComponent>
          </TransformWrapper>
        )}
        {hovered && <HoverPanel el={hovered} />}
        <div className="pointer-events-none absolute right-4 top-4 text-[10px] text-slate-600">
          Scroll to zoom · Drag to pan
        </div>
      </div>
    </div>
  );
}
