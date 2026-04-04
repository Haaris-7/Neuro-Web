"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls, useGLTF, Html } from "@react-three/drei";
import * as THREE from "three";
import { buildLUT, valueToColor, type ColormapName } from "@/lib/colormaps";
import { ColorLegend } from "./color-legend";
import type { RegionBreakdown, FunctionalGroup } from "@/lib/types";

interface BrainHeatmapProps {
  meshUrl: string;
  regionBreakdown: RegionBreakdown[];
  atlasData?: AtlasData | null;
  colormap?: ColormapName;
}

interface AtlasData {
  vertex_labels: number[];
  region_names: string[];
  functional_groups: Record<string, FunctionalGroup>;
}

type ViewMode = "combined" | "attention" | "emotion";

const VIEW_MODES: { key: ViewMode; label: string; groups: FunctionalGroup[] }[] = [
  {
    key: "combined",
    label: "Combined",
    groups: ["visual", "attention", "emotional", "language", "default_mode"],
  },
  { key: "attention", label: "Attention", groups: ["visual", "attention"] },
  { key: "emotion", label: "Emotion", groups: ["emotional"] },
];

function buildVertexColors(
  vertexCount: number,
  atlasData: AtlasData | null,
  regionBreakdown: RegionBreakdown[],
  viewMode: ViewMode,
  colormap: ColormapName,
): Float32Array {
  const colors = new Float32Array(vertexCount * 3);
  const lut = buildLUT(colormap);
  const mode = VIEW_MODES.find((m) => m.key === viewMode)!;

  if (!atlasData) {
    for (let i = 0; i < vertexCount; i++) {
      const [r, g, b] = valueToColor(0.3, lut);
      colors[i * 3] = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;
    }
    return colors;
  }

  const regionScoreMap = new Map<string, number>();
  let maxScore = 0;
  for (const rb of regionBreakdown) {
    if (mode.groups.includes(rb.functional_group)) {
      regionScoreMap.set(rb.region_name, rb.normalized_score);
      maxScore = Math.max(maxScore, rb.normalized_score);
    }
  }

  const regionIdScores = new Map<number, number>();
  for (let idx = 0; idx < atlasData.region_names.length; idx++) {
    const name = atlasData.region_names[idx];
    const score = regionScoreMap.get(name);
    if (score !== undefined && maxScore > 0) {
      regionIdScores.set(idx, score / maxScore);
    }
  }

  for (let i = 0; i < vertexCount; i++) {
    const label = atlasData.vertex_labels[i] ?? -1;
    const normalizedValue = regionIdScores.get(label) ?? 0.05;
    const [r, g, b] = valueToColor(normalizedValue, lut);
    colors[i * 3] = r;
    colors[i * 3 + 1] = g;
    colors[i * 3 + 2] = b;
  }

  return colors;
}

function BrainMesh({
  meshUrl,
  atlasData,
  regionBreakdown,
  viewMode,
  colormap,
  onHover,
}: {
  meshUrl: string;
  atlasData: AtlasData | null;
  regionBreakdown: RegionBreakdown[];
  viewMode: ViewMode;
  colormap: ColormapName;
  onHover: (info: { region: string; group: string; score: number; position: THREE.Vector3 } | null) => void;
}) {
  const { scene } = useGLTF(meshUrl);
  const groupRef = useRef<THREE.Group>(null);
  const colorsRef = useRef<THREE.BufferAttribute | null>(null);
  const { raycaster, pointer, camera } = useThree();

  const meshes = useMemo(() => {
    const result: THREE.Mesh[] = [];
    scene.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        result.push(child);
      }
    });
    return result;
  }, [scene]);

  useEffect(() => {
    meshes.forEach((mesh) => {
      const geom = mesh.geometry;
      const vertexCount = geom.attributes.position.count;
      const vertexColors = buildVertexColors(
        vertexCount,
        atlasData,
        regionBreakdown,
        viewMode,
        colormap,
      );

      const colorAttr = new THREE.BufferAttribute(vertexColors, 3);
      geom.setAttribute("color", colorAttr);
      colorsRef.current = colorAttr;

      mesh.material = new THREE.MeshPhongMaterial({
        vertexColors: true,
        shininess: 30,
        specular: new THREE.Color(0x222222),
        side: THREE.DoubleSide,
      });
    });
  }, [meshes, atlasData, regionBreakdown, viewMode, colormap]);

  useFrame(() => {
    if (!groupRef.current || !atlasData) return;

    raycaster.setFromCamera(pointer, camera);
    const intersects = raycaster.intersectObjects(meshes, false);

    if (intersects.length > 0) {
      const hit = intersects[0];
      const face = hit.face;
      if (face) {
        const vIdx = face.a;
        const labelIdx = atlasData.vertex_labels[vIdx] ?? -1;
        const regionName = atlasData.region_names[labelIdx] || "Unknown";
        const funcGroup = atlasData.functional_groups[regionName] || "default_mode";
        const rb = regionBreakdown.find((r) => r.region_name === regionName);
        onHover({
          region: regionName,
          group: funcGroup,
          score: rb?.normalized_score ?? 0,
          position: hit.point.clone(),
        });
        return;
      }
    }
    onHover(null);
  });

  useEffect(() => {
    if (!groupRef.current || meshes.length === 0) return;
    const box = new THREE.Box3();
    meshes.forEach((m) => box.expandByObject(m));
    const center = box.getCenter(new THREE.Vector3());
    meshes.forEach((m) => m.position.sub(center));
  }, [meshes]);

  return (
    <group ref={groupRef}>
      {meshes.map((mesh, i) => (
        <primitive key={i} object={mesh} />
      ))}
    </group>
  );
}

function HoverTooltip({
  info,
}: {
  info: { region: string; group: string; score: number; position: THREE.Vector3 } | null;
}) {
  if (!info) return null;

  const groupColors: Record<string, string> = {
    visual: "#22d3ee",
    attention: "#3b82f6",
    emotional: "#8b5cf6",
    language: "#34d399",
    default_mode: "#64748b",
  };

  return (
    <Html position={info.position} center style={{ pointerEvents: "none" }}>
      <div className="pointer-events-none -translate-y-full whitespace-nowrap rounded-lg border border-slate-700/80 bg-[#0a0e1a]/95 px-3 py-2 shadow-xl backdrop-blur-sm">
        <p className="text-xs font-semibold text-slate-200">{info.region}</p>
        <div className="mt-1 flex items-center gap-2">
          <span
            className="h-1.5 w-1.5 rounded-full"
            style={{ background: groupColors[info.group] || "#64748b" }}
          />
          <span className="text-[10px] capitalize text-slate-400">
            {info.group.replace("_", " ")}
          </span>
          <span
            className="ml-1 font-mono text-[10px] font-bold"
            style={{ color: groupColors[info.group] || "#64748b" }}
          >
            {info.score.toFixed(1)}
          </span>
        </div>
      </div>
    </Html>
  );
}

export function BrainHeatmap({
  meshUrl,
  regionBreakdown,
  atlasData = null,
  colormap = "viridis",
}: BrainHeatmapProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("combined");
  const [hoveredRegion, setHoveredRegion] = useState<{
    region: string;
    group: string;
    score: number;
    position: THREE.Vector3;
  } | null>(null);

  const handleHover = useCallback(
    (
      info: {
        region: string;
        group: string;
        score: number;
        position: THREE.Vector3;
      } | null,
    ) => {
      setHoveredRegion(info);
    },
    [],
  );

  return (
    <div className="flex h-full flex-col">
      {/* View mode toggles */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex gap-1 rounded-xl bg-slate-900/60 p-1">
          {VIEW_MODES.map((mode) => (
            <button
              key={mode.key}
              onClick={() => setViewMode(mode.key)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                viewMode === mode.key
                  ? "bg-slate-700/80 text-slate-100 shadow-sm"
                  : "text-slate-500 hover:text-slate-300"
              }`}
            >
              {mode.label}
            </button>
          ))}
        </div>
        {hoveredRegion && (
          <div className="flex items-center gap-2 text-xs text-slate-400">
            <span className="font-medium text-slate-300">
              {hoveredRegion.region}
            </span>
            <span className="font-mono text-cyan-400">
              {hoveredRegion.score.toFixed(1)}
            </span>
          </div>
        )}
      </div>

      {/* 3D Canvas */}
      <div className="relative flex-1 overflow-hidden rounded-2xl border border-slate-800/40 bg-[#060a14]">
        <Canvas
          camera={{ position: [0, 0, 200], fov: 45, near: 1, far: 1000 }}
          dpr={[1, Math.min(window.devicePixelRatio, 2)]}
          gl={{ antialias: true, alpha: false }}
        >
          <color attach="background" args={["#060a14"]} />
          <ambientLight intensity={0.5} />
          <directionalLight position={[100, 80, 100]} intensity={0.8} />
          <directionalLight position={[-100, -40, -60]} intensity={0.3} />

          <BrainMesh
            meshUrl={meshUrl}
            atlasData={atlasData}
            regionBreakdown={regionBreakdown}
            viewMode={viewMode}
            colormap={colormap}
            onHover={handleHover}
          />

          <HoverTooltip info={hoveredRegion} />

          <OrbitControls
            enableDamping
            dampingFactor={0.08}
            rotateSpeed={0.6}
            zoomSpeed={0.8}
            minDistance={80}
            maxDistance={400}
          />
        </Canvas>

        <div className="pointer-events-none absolute bottom-4 left-4 right-4">
          <ColorLegend colormap={colormap} min={0} max={10} />
        </div>

        <div className="pointer-events-none absolute right-4 top-4 text-[10px] text-slate-600">
          Drag to rotate · Scroll to zoom
        </div>
      </div>
    </div>
  );
}
