export interface ModelMetadata {
  id: string;
  filename: string;
  size: number;
  uploaded_at: string;
  status: "ready" | "invalid";
}

export type JobStatus = "queued" | "loading_model" | "processing" | "completed" | "failed";

export interface ImageInfo {
  width: number;
  height: number;
}

export interface TileInfo {
  tile_size: number;
  overlap: number;
  columns: number;
  rows: number;
  total: number;
}

export type DegradationMode = "direct" | "synthetic_noise" | "blur" | "broken" | "missing" | "occlusion";

export interface MetricsInfo {
  psnr_vs_input: number;
  ssim_vs_input: number;
  psnr_vs_ground_truth: number | null;
  ssim_vs_ground_truth: number | null;
}

export interface PageResult {
  output_id: string;
  degraded_id: string | null;
  output_url: string;
  degraded_url: string | null;
  input: ImageInfo;
  output: ImageInfo;
  tiles: TileInfo;
  metrics: MetricsInfo;
}

export interface InferenceStatus {
  job_id: string;
  status: JobStatus;
  progress: number;
  processed_tiles: number;
  total_tiles: number;
  elapsed_seconds: number;
  error: string | null;
  input: ImageInfo | null;
  output: ImageInfo | null;
  tiles: TileInfo | null;
  output_url: string | null;
  degraded_url: string | null;
  pages: PageResult[];
  processing_time_seconds: number | null;
  metrics: MetricsInfo | null;
}

export interface InferenceSettings {
  tile_size: number;
  tile_overlap: number;
  processing_mode: "tile" | "full_image";
  batch_size: number;
  device: "auto" | "cpu" | "cuda";
  degradation_mode: DegradationMode;
  noise_sigma: number;
  degradation_strength: number;
}

export interface HistoryRecord {
  job_id: string;
  input_filename: string;
  model_filename: string;
  input_id?: string | null;
  output_id: string | null;
  output_ids?: string[];
  degraded_ids?: string[];
  degraded_id?: string | null;
  deleted_at?: string | null;
  degradation_mode?: DegradationMode | null;
  degradation_strength?: number | null;
  status: JobStatus;
  processing_time_seconds: number | null;
  created_at: string;
}

export interface SystemInfo {
  device: string;
  cuda_available: boolean;
  gpu_name: string | null;
  cpu: string;
  ram_gb: number;
}

export interface AuthUser {
  id: string;
  username: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: number;
}
