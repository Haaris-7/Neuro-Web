export type FunctionalGroup =
  | "visual"
  | "attention"
  | "emotional"
  | "language"
  | "default_mode";

export const FUNCTIONAL_GROUPS: FunctionalGroup[] = [
  "visual",
  "attention",
  "emotional",
  "language",
  "default_mode",
];

export const GROUP_COLORS: Record<FunctionalGroup, string> = {
  visual: "#22d3ee",
  attention: "#3b82f6",
  emotional: "#8b5cf6",
  language: "#34d399",
  default_mode: "#64748b",
};

export const GROUP_LABELS: Record<FunctionalGroup, string> = {
  visual: "Visual",
  attention: "Attention",
  emotional: "Emotional",
  language: "Language",
  default_mode: "Default mode",
};

export interface NetworkBreakdown {
  network: FunctionalGroup;
  regions: string[];
  n_vertices: number;
  mean_activation: number;
  normalized_score: number;
}

export interface RegionBreakdown {
  region_name: string;
  functional_group: FunctionalGroup | null;
  n_vertices: number;
  mean_activation: number;
  normalized_score: number;
}

export interface TimestepScore {
  attention: number;
  emotion: number;
  overall: number;
}

export interface ScoreReport {
  attention_score: number;
  emotion_score: number;
  impact_score: number;
  temporal_variance: number;
  network_breakdown: NetworkBreakdown[];
  region_breakdown: RegionBreakdown[];
  per_timestep_scores: TimestepScore[];
}

export type DarkPatternType =
  | "urgency"
  | "confirmshaming"
  | "pre_checked"
  | "hidden_costs"
  | "misdirection"
  | "forced_continuity";

export interface BBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface DarkPatternMatch {
  pattern_type: DarkPatternType;
  confidence: number;
  evidence_text: string;
  bbox: BBox | null;
}

export interface DarkPatternReport {
  patterns: DarkPatternMatch[];
  score: number;
  summary: string;
  counts: Partial<Record<DarkPatternType, number>>;
}

export interface TimelinePoint {
  timestep: number;
  time_s: number;
  scroll_position_px: number;
  overall_intensity: number;
  attention_intensity: number;
  emotion_intensity: number;
  language_intensity: number;
  region_breakdown: Record<FunctionalGroup, number>;
}

export interface PeakAnnotation {
  timestep: number;
  time_s: number;
  scroll_position_px: number;
  intensity: number;
  dominant_group: FunctionalGroup;
  description: string;
}

export interface TimelineData {
  series: TimelinePoint[];
  peaks: PeakAnnotation[];
  duration_s: number;
}

export interface ElementOverlay {
  tag: string;
  bbox: BBox;
  intensity: number;
  attention_contrib: number;
  emotion_contrib: number;
  visible_timesteps: number[];
}

export interface VertexActivationMeta {
  file: string;
  dtype: "uint8";
  n_vertices: number;
  n_timesteps: number;
  layout: string;
  vmin: number;
  vmax: number;
}

export interface TemplateSummaries {
  overall: string;
  attention: string;
  emotion: string;
  impact: string;
  dark_patterns: string;
  temporal_dynamics: string;
}

export type InferenceBackend = "tribe" | "mock";

export interface ReportMetadata {
  url: string;
  capture_date: string;
  inference_backend: InferenceBackend;
  modalities: string[];
  n_timesteps: number;
  n_vertices: number;
  n_words: number | null;
  hemodynamic_offset_s: number | null;
  colormap: string;
  viewport_w: number;
  viewport_h: number;
  page_height: number | null;
  capture_duration_s: number | null;
  video_duration_s: number | null;
  atlas: string;
  mesh: string;
}

export interface AnalysisReport {
  job_id: string;
  url: string;
  scores: ScoreReport;
  dark_patterns: DarkPatternReport;
  timeline: TimelineData;
  overlay: ElementOverlay[];
  vertex_activation: VertexActivationMeta;
  projection_paths: Record<string, string>;
  template_summaries: TemplateSummaries;
  metadata: ReportMetadata;
}

export interface AtlasData {
  version: number;
  atlas: string;
  mesh: string;
  n_vertices_lh: number;
  n_vertices_rh: number;
  region_names: string[];
  vertex_labels: number[];
  functional_groups: Record<FunctionalGroup, string[]>;
  medial_wall: string[];
}

export interface HealthResponse {
  inference_backend: InferenceBackend;
  modalities: string[];
  inference_ready: boolean;
  model_loaded: boolean;
  gpu_available: boolean;
  llm_available: boolean;
  llm_provider: string | null;
  error: string | null;
}

export interface JobResponse {
  id: string;
  url: string;
  status: string;
  failed_stage: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  capture_metadata: Record<string, unknown> | null;
  config: Record<string, unknown> | null;
}

export function jobFileUrl(jobId: string, relativePath: string): string {
  const encoded = relativePath.split("/").map(encodeURIComponent).join("/");
  return `/api/jobs/${encodeURIComponent(jobId)}/files/${encoded}`;
}
