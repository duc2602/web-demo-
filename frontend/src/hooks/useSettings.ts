import { useCallback, useEffect, useState } from "react";
import { InferenceSettings } from "../types";

const STORAGE_KEY = "ai-model-tester:settings";

const DEFAULT_SETTINGS: InferenceSettings = {
  tile_size: 128,
  tile_overlap: 16,
  processing_mode: "tile",
  batch_size: 1,
  device: "auto",
  degradation_mode: "direct",
  noise_sigma: 25,
  degradation_strength: 25,
};

function readSettings(): InferenceSettings {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    const savedSettings = JSON.parse(raw) as Partial<InferenceSettings>;
    return {
      ...DEFAULT_SETTINGS,
      ...savedSettings,
      processing_mode: savedSettings.processing_mode === "full_image" ? "tile" : savedSettings.processing_mode ?? DEFAULT_SETTINGS.processing_mode,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

export function useSettings() {
  const [settings, setSettings] = useState<InferenceSettings>(readSettings);

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  }, [settings]);

  const update = useCallback((partial: Partial<InferenceSettings>) => {
    setSettings((prev) => ({ ...prev, ...partial }));
  }, []);

  return { settings, update };
}
