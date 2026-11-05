import { useEffect, useState } from "react";
import { useAppContext } from "../context/AppContext";
import { api } from "../services/api";
import { SystemInfo } from "../types";

export default function Settings() {
  const { settings, updateSettings } = useAppContext();
  const [system, setSystem] = useState<SystemInfo | null>(null);

  useEffect(() => {
    api.get("/api/system").then((r) => setSystem(r.data)).catch(() => {});
  }, []);

  return (
    <div className="max-w-2xl mx-auto px-8 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-white tracking-tight">Settings</h1>
        <p className="text-sm text-muted mt-1">Inference defaults for new jobs</p>
      </header>

      <div className="card p-5 space-y-5">
        <Field label="Tile Size">
          <input
            type="number"
            min={32}
            step={8}
            value={settings.tile_size}
            onChange={(e) => updateSettings({ tile_size: Number(e.target.value) })}
            className="input"
          />
        </Field>

        <Field label="Tile Overlap">
          <input
            type="number"
            min={0}
            max={settings.tile_size - 8}
            value={settings.tile_overlap}
            onChange={(e) => updateSettings({ tile_overlap: Number(e.target.value) })}
            className="input"
          />
        </Field>

        <Field label="Processing Mode">
          <select
            value={settings.processing_mode}
            onChange={(e) => updateSettings({ processing_mode: e.target.value as "tile" | "full_image" })}
            className="input"
          >
            <option value="tile">Tile (128×128, safe for large images, shows progress)</option>
            <option value="full_image">Full Image (fastest, needs more VRAM)</option>
          </select>
        </Field>

        <Field label="Device">
          <select
            value={settings.device}
            onChange={(e) => updateSettings({ device: e.target.value as "auto" | "cpu" | "cuda" })}
            className="input"
          >
            <option value="auto">Auto</option>
            <option value="cpu">CPU</option>
            <option value="cuda" disabled={system !== null && !system.cuda_available}>
              {system !== null && !system.cuda_available ? "CUDA (không khả dụng trên máy này)" : "CUDA"}
            </option>
          </select>
        </Field>

        <Field label="Batch Size">
          <input
            type="number"
            min={1}
            max={64}
            value={settings.batch_size}
            onChange={(e) => updateSettings({ batch_size: Number(e.target.value) })}
            className="input"
          />
        </Field>

        <Field label="Degradation Mode">
          <select
            value={settings.degradation_mode}
            onChange={(e) => updateSettings({ degradation_mode: e.target.value as typeof settings.degradation_mode })}
            className="input"
            aria-label="Degradation Mode"
          >
            <option value="direct">Direct input</option>
            <option value="synthetic_noise">Gaussian noise</option>
            <option value="blur">Blur</option>
            <option value="broken">Broken strokes</option>
            <option value="missing">Missing regions</option>
            <option value="occlusion">Occlusion</option>
          </select>
        </Field>

        {settings.degradation_mode === "synthetic_noise" && (
          <Field label="Noise Sigma">
            <input
              type="number"
              min={1}
              max={100}
              step={1}
              value={settings.noise_sigma}
              onChange={(e) => updateSettings({ noise_sigma: Number(e.target.value) })}
              className="input"
            />
          </Field>
        )}

        {settings.degradation_mode !== "direct" && settings.degradation_mode !== "synthetic_noise" && (
          <Field label="Degradation Strength">
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={100}
                value={settings.degradation_strength}
                onChange={(e) => updateSettings({ degradation_strength: Number(e.target.value) })}
                className="w-full accent-accent"
                aria-label="Degradation Strength"
              />
              <span className="w-9 text-right text-xs text-zinc-300">{settings.degradation_strength}%</span>
            </div>
          </Field>
        )}

        {settings.degradation_mode !== "direct" && (
          <p className="text-xs leading-relaxed text-zinc-400">
            The uploaded image is treated as clean, degraded, then sent to the model for restoration.
          </p>
        )}
      </div>

      <div className="card p-5 mt-5">
        <p className="text-sm font-medium text-white mb-3">System</p>
        {system ? (
          <div className="space-y-1.5 text-sm">
            <Row label="Status" value={system.cuda_available ? "● CUDA Available" : "● CPU Mode"} />
            {system.gpu_name && <Row label="GPU" value={system.gpu_name} />}
            <Row label="CPU" value={system.cpu} />
            <Row label="RAM" value={`${system.ram_gb} GB`} />
          </div>
        ) : (
          <p className="text-xs text-muted">Loading system info...</p>
        )}
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <label className="text-sm text-white">{label}</label>
      <div className="w-56">{children}</div>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-muted">{label}</span>
      <span className="text-white">{value}</span>
    </div>
  );
}
