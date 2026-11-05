import { api } from "./api";
import { ModelMetadata } from "../types";

export async function uploadModel(
  file: File,
  onProgress?: (percent: number) => void
): Promise<ModelMetadata> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<ModelMetadata>("/api/models/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress: (evt) => {
      if (onProgress && evt.total) {
        onProgress(Math.round((evt.loaded / evt.total) * 100));
      }
    },
  });
  return response.data;
}

export async function listModels(): Promise<ModelMetadata[]> {
  const response = await api.get<{ models: ModelMetadata[] }>("/api/models");
  return response.data.models;
}

export async function deleteModel(modelId: string): Promise<void> {
  await api.delete(`/api/models/${modelId}`);
}
