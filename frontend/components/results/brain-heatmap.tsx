"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree, type ThreeEvent } from "@react-three/fiber";
import { OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";
import { buildLUT, valueToColor, type ColormapName } from "@/lib/colormaps";
import { ColorLegend } from "./color-legend";
import {
  GROUP_COLORS,
  GROUP_LABELS,
  type AtlasData,
  type FunctionalGroup,
  type RegionBreakdown,
  type VertexActivationMeta,
} from "@/lib/types";

interface BrainHeatmapProps {
  meshUrl: string;
  activationUrl: string;
  activationMeta: VertexActivationMeta;
  atlas: AtlasData | null;
  regionBreakdown: RegionBreakdown[];
  timeLabels: number[];
  colormap?: ColormapName;
}

type ViewMode = "all" | FunctionalGroup;

const VIEW_MODES: { key: ViewMode; label: string }[] = [
  { key: "all", label: "All cortex" },
  { key: "visual", label: "Visual" },
  { key: "attention", label: "Attention" },
  { key: "emotional", label: "Emotional" },
  { key: "language", label: "Language" },
  { key: "default_mode", label: "Default mode" },
];

const DIMMED = new THREE.Color("#1a2233");
const MEDIAL_WALL = new THREE.Color("#0f1522");

interface HoverInfo {
  region: string;
  group: FunctionalGroup | null;
  score: number | null;
  value: number;
}

interface HemisphereMesh {
  mesh: THREE.Mesh;
  offset: number;
}

function useVertexActivation(url: string, meta: VertexActivationMeta) {
  const [data, setData] = useState<Uint8Array | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Activation data unavailable (${res.status})`);
        const buf = new Uint8Array(await res.arrayBuffer());
        const expected = (meta.n_timesteps + 1) * meta.n_vertices;
        if (buf.length !== expected) {
          throw new Error(`Activation data has ${buf.length} bytes, expected ${expected}`);
        }
        if (!cancelled) setData(buf);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load activation");
      });
    return () => {
      cancelled = true;
    };
  }, [url, meta.n_timesteps, meta.n_vertices]);
  return { data, error };
}

function regionMask(atlas: AtlasData, mode: ViewMode): Uint8Array | null {
  if (mode === "all") return null;
  const allowed = new Set(
    (atlas.functional_groups[mode] ?? []).map((name) => atlas.region_names.indexOf(name)),
  );
  const mask = new Uint8Array(atlas.vertex_labels.length);
  for (let i = 0; i < mask.length; i++) {
    mask[i] = allowed.has(atlas.vertex_labels[i]) ? 1 : 0;
  }
  return mask;
}

function paintHemisphere(
  hemi: HemisphereMesh,
  frame: Uint8Array,
  frameOffset: number,
  mask: Uint8Array | null,
  wall: Uint8Array | null,
  lut: Float32Array,
) {
  const geom = hemi.mesh.geometry as THREE.BufferGeometry;
  const count = geom.attributes.position.count;
  let attr = geom.getAttribute("color") as THREE.BufferAttribute | undefined;
  if (!attr || attr.count !== count) {
    attr = new THREE.BufferAttribute(new Float32Array(count * 3), 3);
    geom.setAttribute("color", attr);
  }
  const colors = attr.array as Float32Array;
  for (let i = 0; i < count; i++) {
    const v = hemi.offset + i;
    let r: number, g: number, b: number;
    if (wall && wall[v]) {
      ({ r, g, b } = MEDIAL_WALL);
    } else if (mask && !mask[v]) {
      ({ r, g, b } = DIMMED);
    } else {
      [r, g, b] = valueToColor(frame[frameOffset + v] / 255, lut);
    }
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }
  attr.needsUpdate = true;
}

function groupOf(atlas: AtlasData, region: string): FunctionalGroup | null {
  for (const [group, regions] of Object.entries(atlas.functional_groups)) {
    if (regions.includes(region)) return group as FunctionalGroup;
  }
  return null;
}

function BrainMesh({
  meshUrl,
  activation,
  meta,
  atlas,
  regionBreakdown,
  mode,
  frameIndex,
  colormap,
  onHover,
}: {
  meshUrl: string;
  activation: Uint8Array | null;
  meta: VertexActivationMeta;
  atlas: AtlasData | null;
  regionBreakdown: RegionBreakdown[];
  mode: ViewMode;
  frameIndex: number;
  colormap: ColormapName;
  onHover: (info: HoverInfo | null) => void;
}) {
  const { scene } = useGLTF(meshUrl);
  const { camera } = useThree();

  const hemispheres = useMemo<HemisphereMesh[]>(() => {
    const found: HemisphereMesh[] = [];
    let running = 0;
    const meshes: THREE.Mesh[] = [];
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) meshes.push(child);
    });
    meshes.sort((a, b) => {
      const aLeft = /left/i.test(a.name) || /left/i.test(a.parent?.name ?? "");
      const bLeft = /left/i.test(b.name) || /left/i.test(b.parent?.name ?? "");
      return Number(bLeft) - Number(aLeft);
    });
    for (const mesh of meshes) {
      mesh.material = new THREE.MeshStandardMaterial({
        vertexColors: true,
        roughness: 0.75,
        metalness: 0.05,
        flatShading: false,
      });
      const geom = mesh.geometry as THREE.BufferGeometry;
      if (!geom.getAttribute("normal")) geom.computeVertexNormals();
      found.push({ mesh, offset: running });
      running += geom.attributes.position.count;
    }
    const box = new THREE.Box3();
    meshes.forEach((m) => box.expandByObject(m));
    const center = box.getCenter(new THREE.Vector3());
    meshes.forEach((m) => m.position.sub(center));
    return found;
  }, [scene]);

  useEffect(() => {
    const size = new THREE.Box3().setFromObject(scene).getSize(new THREE.Vector3()).length();
    camera.position.set(0, size * 0.25, size * 0.95);
    camera.lookAt(0, 0, 0);
  }, [scene, camera]);

  const wall = useMemo(() => {
    if (!atlas) return null;
    const wallCodes = new Set(atlas.medial_wall.map((n) => atlas.region_names.indexOf(n)));
    const arr = new Uint8Array(atlas.vertex_labels.length);
    for (let i = 0; i < arr.length; i++) arr[i] = wallCodes.has(atlas.vertex_labels[i]) ? 1 : 0;
    return arr;
  }, [atlas]);

  const mask = useMemo(() => (atlas ? regionMask(atlas, mode) : null), [atlas, mode]);
  const lut = useMemo(() => buildLUT(colormap), [colormap]);

  useEffect(() => {
    if (!activation) return;
    const frameOffset = frameIndex * meta.n_vertices;
    hemispheres.forEach((hemi) => paintHemisphere(hemi, activation, frameOffset, mask, wall, lut));
  }, [activation, frameIndex, hemispheres, mask, wall, lut, meta.n_vertices]);

  const regionScores = useMemo(
    () => new Map(regionBreakdown.map((r) => [r.region_name, r.normalized_score])),
    [regionBreakdown],
  );

  const handleMove = useCallback(
    (hemi: HemisphereMesh) => (event: ThreeEvent<PointerEvent>) => {
      event.stopPropagation();
      if (!atlas || !activation || !event.face) return;
      const v = hemi.offset + event.face.a;
      const label = atlas.vertex_labels[v];
      const region = atlas.region_names[label] ?? "unknown";
      const group = groupOf(atlas, region);
      onHover({
        region,
        group,
        score: regionScores.get(region) ?? null,
        value: activation[frameIndex * meta.n_vertices + v] / 255,
      });
    },
    [atlas, activation, frameIndex, meta.n_vertices, onHover, regionScores],
  );

  return (
    <group>
      {hemispheres.map((hemi) => (
        <primitive
          key={hemi.mesh.uuid}
          object={hemi.mesh}
          onPointerMove={handleMove(hemi)}
          onPointerOut={() => onHover(null)}
        />
      ))}
    </group>
  );
}

export function BrainHeatmap({
  meshUrl,
  activationUrl,
  activationMeta,
  atlas,
  regionBreakdown,
  timeLabels,
  colormap = "viridis",
}: BrainHeatmapProps) {
  const [mode, setMode] = useState<ViewMode>("all");
  const [frame, setFrame] = useState(0);
  const [hover, setHover] = useState<HoverInfo | null>(null);
  const [playing, setPlaying] = useState(false);
  const { data: activation, error } = useVertexActivation(activationUrl, activationMeta);
  const playRef = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    playRef.current = window.setInterval(() => {
      setFrame((f) => (f >= activationMeta.n_timesteps ? 1 : f + 1));
    }, 700);
    return () => {
      if (playRef.current) window.clearInterval(playRef.current);
    };
  }, [playing, activationMeta.n_timesteps]);

  const frameLabel =
    frame === 0
      ? "Time-averaged"
      : `t = ${(timeLabels[frame - 1] ?? frame - 1).toFixed(1)}s`;

  return (
    <div className="flex h-full flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1 rounded-xl bg-slate-900/60 p-1">
          {VIEW_MODES.map((m) => (
            <button
              key={m.key}
              onClick={() => setMode(m.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                mode === m.key
                  ? "bg-slate-700/80 text-slate-100 shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {m.key !== "all" && (
                <span
                  className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full align-middle"
                  style={{ background: GROUP_COLORS[m.key] }}
                />
              )}
              {m.label}
            </button>
          ))}
        </div>
        <div className="flex min-h-[1.5rem] items-center gap-2 text-xs text-slate-400">
          {hover ? (
            <>
              <span className="font-medium text-slate-200">{hover.region}</span>
              {hover.group && (
                <span className="capitalize" style={{ color: GROUP_COLORS[hover.group] }}>
                  {GROUP_LABELS[hover.group]}
                </span>
              )}
              {hover.score !== null && (
                <span className="font-mono text-cyan-300">{hover.score.toFixed(1)}/10</span>
              )}
            </>
          ) : (
            <span className="text-slate-600">Hover the cortex to inspect a region</span>
          )}
        </div>
      </div>

      <div className="relative flex-1 overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14]">
        <Canvas
          camera={{ fov: 40, near: 1, far: 2000, position: [0, 40, 260] }}
          dpr={[1, 2]}
          gl={{ antialias: true, alpha: false }}
        >
          <color attach="background" args={["#060a14"]} />
          <hemisphereLight args={["#dbe7ff", "#0b1020", 0.9]} />
          <directionalLight position={[120, 100, 120]} intensity={1.1} />
          <directionalLight position={[-120, -40, -80]} intensity={0.35} />
          <BrainMesh
            meshUrl={meshUrl}
            activation={activation}
            meta={activationMeta}
            atlas={atlas}
            regionBreakdown={regionBreakdown}
            mode={mode}
            frameIndex={frame}
            colormap={colormap}
            onHover={setHover}
          />
          <OrbitControls
            enableDamping
            dampingFactor={0.08}
            rotateSpeed={0.6}
            zoomSpeed={0.8}
            minDistance={90}
            maxDistance={500}
          />
        </Canvas>

        {error && (
          <div className="absolute inset-x-4 top-4 rounded-lg border border-amber-500/30 bg-amber-950/70 px-3 py-2 text-xs text-amber-200">
            {error}
          </div>
        )}
        {!atlas && !error && (
          <div className="absolute right-4 top-4 rounded-lg border border-slate-700/60 bg-slate-900/70 px-3 py-1.5 text-[10px] text-slate-400">
            Loading atlas…
          </div>
        )}

        <div className="pointer-events-none absolute bottom-4 left-4 right-4">
          <ColorLegend
            colormap={colormap}
            min={0}
            max={1}
            label={`Predicted activation · ${frameLabel}`}
          />
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-xl border border-slate-800/50 bg-slate-900/40 px-4 py-2">
        <button
          onClick={() => setPlaying((p) => !p)}
          disabled={activationMeta.n_timesteps < 2}
          className="flex h-7 w-7 items-center justify-center rounded-lg bg-slate-800 text-slate-300 transition hover:bg-slate-700 disabled:opacity-40"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
              <rect x="5" y="4" width="5" height="16" />
              <rect x="14" y="4" width="5" height="16" />
            </svg>
          ) : (
            <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor">
              <path d="M6 4l14 8-14 8z" />
            </svg>
          )}
        </button>
        <input
          type="range"
          min={0}
          max={activationMeta.n_timesteps}
          step={1}
          value={frame}
          onChange={(e) => {
            setPlaying(false);
            setFrame(parseInt(e.target.value, 10));
          }}
          className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-slate-700 accent-cyan-400"
        />
        <span className="w-28 text-right font-mono text-[11px] text-slate-400">{frameLabel}</span>
      </div>
    </div>
  );
}
