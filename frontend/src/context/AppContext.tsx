import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { InferenceSettings, InferenceStatus, ModelMetadata } from "../types";

const SETTINGS_KEY = "ai-model-tester:settings";

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
    const raw = localStorage.getItem(SETTINGS_KEY);
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

interface WorkspaceState {
  selectedModel: ModelMetadata | null;
  setSelectedModel: (m: ModelMetadata | null) => void;
  imageFile: File | null;
  inputPreviewUrl: string | null;
  setImage: (file: File | null) => void;
  status: InferenceStatus | null;
  setStatus: (s: InferenceStatus | null) => void;
  running: boolean;
  setRunning: (r: boolean) => void;
}

interface AppContextValue {
  settings: InferenceSettings;
  updateSettings: (partial: Partial<InferenceSettings>) => void;
  workspace: WorkspaceState;
}

const AppContext = createContext<AppContextValue | null>(null);

export function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useAppContext must be used within AppProvider");
  return ctx;
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<InferenceSettings>(readSettings);

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  const updateSettings = (partial: Partial<InferenceSettings>) => {
    setSettings((prev) => ({ ...prev, ...partial }));
  };

  const [selectedModel, setSelectedModel] = useState<ModelMetadata | null>(null);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [inputPreviewUrl, setInputPreviewUrl] = useState<string | null>(null);
  const [status, setStatus] = useState<InferenceStatus | null>(null);
  const [running, setRunning] = useState(false);

  function setImage(file: File | null) {
    setImageFile(file);
    setInputPreviewUrl(file ? URL.createObjectURL(file) : null);
    setStatus(null);
  }

  const workspace: WorkspaceState = {
    selectedModel,
    setSelectedModel,
    imageFile,
    inputPreviewUrl,
    setImage,
    status,
    setStatus,
    running,
    setRunning,
  };

  return (
    <AppContext.Provider value={{ settings, updateSettings, workspace }}>
      {children}
    </AppContext.Provider>
  );
}