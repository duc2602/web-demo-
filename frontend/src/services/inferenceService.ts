import { API_BASE_URL, api } from "./api";
import { HistoryRecord, InferenceSettings, InferenceStatus } from "../types";

export async function startInference(
  modelId: string,
  imageFile: File,
  settings: InferenceSettings
): Promise<{ job_id: string; status: string }> {
  const formData = new FormData();
  formData.append("model_id", modelId);
  formData.append("input_image", imageFile);
  formData.append("tile_size", String(settings.tile_size));
  formData.append("tile_overlap", String(settings.tile_overlap));
  formData.append("batch_size", String(settings.batch_size));
  formData.append("device", settings.device);
  formData.append("processing_mode", settings.processing_mode);
  formData.append("degradation_mode", settings.degradation_mode);
  formData.append("noise_sigma", String(settings.noise_sigma));
  formData.append("degradation_strength", String(settings.degradation_strength));

  const response = await api.post("/api/inference", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function getInferenceStatus(jobId: string): Promise<InferenceStatus> {
  const response = await api.get<InferenceStatus>(`/api/inference/${jobId}`);
  return response.data;
}

export async function getHistory(): Promise<HistoryRecord[]> {
  const response = await api.get<HistoryRecord[]>("/api/inference/history");
  return response.data;
}

export async function deleteHistory(jobId: string): Promise<void> {
  await api.delete(`/api/inference/history/${jobId}`);
}


export async function getTrash(): Promise<HistoryRecord[]> {
  const response = await api.get<HistoryRecord[]>("/api/inference/trash");
  return response.data;
}

export async function restoreHistory(jobId: string): Promise<void> {
  await api.post(`/api/inference/trash/${jobId}/restore`);
}

export async function permanentlyDeleteHistory(jobId: string): Promise<void> {
  await api.delete(`/api/inference/trash/${jobId}`);
}

export function outputImageUrl(outputUrl: string): string {
  return `${API_BASE_URL}${outputUrl}`;
}

export function degradedImageUrl(degradedUrl: string): string {
  return `${API_BASE_URL}${degradedUrl}`;
}

/** Returns true if the job is in a terminal state. */
export function isTerminalStatus(status: InferenceStatus): boolean {
  return status.status === "completed" || status.status === "failed";
}

/** Returns true if the job is in a terminal state and has an output image. */
export function hasOutputImage(status: InferenceStatus): boolean {
  return isTerminalStatus(status) && status.output_url !== null;
}   

/** Polls job status every `intervalMs` until it reaches a terminal state. */
export function pollInference(
  jobId: string,
  onUpdate: (status: InferenceStatus) => void,
  intervalMs = 800
): () => void {
  let cancelled = false;

  async function tick() {
    if (cancelled) return;
    try {
      const status = await getInferenceStatus(jobId);
      onUpdate(status);
      if (status.status === "completed" || status.status === "failed") {
        return;
      }
    } catch {
      // transient error - keep polling
    }
    if (!cancelled) {
      setTimeout(tick, intervalMs);
    }
  }

  tick();
  return () => {
    cancelled = true;
  };
}
