import axios from "axios";

// Production is same-origin; Vite proxies /api to the backend during development.
export const API_BASE_URL = "";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

export function extractErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}
export function extractErrorCode(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const code = error.response?.data?.code;
    if (typeof code === "string") return code;
  }
  return fallback;
}
export function extractErrorStatus(error: unknown, fallback: number): number {
  if (axios.isAxiosError(error)) {
    const status = error.response?.status;
    if (typeof status === "number") return status;
  }
  return fallback;
}
