export interface RegionBreakdown {
  region_name: string;
  functional_group: FunctionalGroup;
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

export interface DarkPatternBBox {
  tag: string;
  x: number;
  y: number;
  width: number;
  height: number;
  scroll_y: number;
}

export interface DarkPatternMatch {
  pattern_type: DarkPatternType;
  confidence: number;
  evidence_text: string;
  dom_selector: string | null;
  bbox: DarkPatternBBox | null;
}

export interface DarkPatternReport {
  patterns: DarkPatternMatch[];
  score: number;
  summary: string;
}

export type FunctionalGroup =
  | "visual"
  | "attention"
  | "emotional"
  | "language"
  | "default_mode";

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
  intensity: number;
  dominant_group: string;
  description: string;
}

export interface TimelineData {
  series: TimelinePoint[];
  peaks: PeakAnnotation[];
  duration_s: number;
}

export interface ElementOverlay {
  tag: string;
  bbox: { x: number; y: number; width: number; height: number };
  intensity: number;
  attention_contrib: number;
  emotion_contrib: number;
  visible_timesteps: number[];
}

export interface TemplateSummaries {
  overall: string;
  attention: string;
  emotion: string;
  impact: string;
  dark_patterns: string;
  temporal_dynamics: string;
}

export interface ReportMetadata {
  url: string;
  capture_date: string;
  n_timesteps: number;
  n_vertices: number;
  colormap: string;
  viewport_height: number;
  capture_duration_s?: number;
  viewport_w?: number;
  viewport_h?: number;
}

export interface AnalysisReport {
  job_id: string;
  url: string;
  scores: ScoreReport;
  dark_patterns: DarkPatternReport;
  timeline: TimelineData;
  overlay: ElementOverlay[];
  heatmap_colors_path: string | null;
  projection_paths: Record<string, string>;
  template_summaries: TemplateSummaries;
  metadata: ReportMetadata;
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
