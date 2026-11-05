import { useRef, useState } from "react";
import { UploadCloud, CheckCircle2, X, RefreshCw } from "lucide-react";
import { ModelMetadata } from "../types";
import { formatBytes } from "../utils/format";
import { uploadModel } from "../services/modelService";
import { useToast } from "./Toast";
import { extractErrorMessage } from "../services/api";

interface Props {
  selectedModel: ModelMetadata | null;
  onModelReady: (model: ModelMetadata) => void;
  onClear: () => void;
}

export default function ModelUploader({ selectedModel, onModelReady, onClear }: Props) {
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const { push } = useToast();

  async function handleFile(file: File) {
    setUploading(true);
    setProgress(0);
    try {
      const model = await uploadModel(file, setProgress);
      onModelReady(model);
      push("success", `Model "${model.filename}" uploaded.`);
    } catch (err) {
      push("error", extractErrorMessage(err, "Failed to upload model."));
    } finally {
      setUploading(false);
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  return (
    <div className="card p-5">
      <p className="text-sm font-medium text-white mb-3 tracking-tight">Model</p>

      {!selectedModel && !uploading && (
        <div
          className={`dropzone ${dragActive ? "active" : ""} flex flex-col items-center justify-center py-10 cursor-pointer`}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
        >
          <div className="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-3">
            <UploadCloud size={18} className="text-muted" />
          </div>
          <p className="text-sm text-white">Drop model here</p>
          <p className="text-xs text-muted mt-1">or click to browse</p>
          <p className="text-xs text-muted mt-3">Supports .pth, .pt</p>
          <input
            ref={inputRef}
            type="file"
            accept=".pth,.pt"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      )}

      {uploading && (
        <div className="py-8">
          <div className="flex items-center justify-between text-xs text-muted mb-2">
            <span>Uploading...</span>
            <span>{progress}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
            <div
              className="h-full bg-accent transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {selectedModel && !uploading && (
        <div className="flex items-center justify-between bg-white/[0.03] rounded-lg px-4 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <CheckCircle2 size={18} className="text-success shrink-0" />
            <div className="min-w-0">
              <p className="text-sm text-white truncate">{selectedModel.filename}</p>
              <p className="text-xs text-muted">{formatBytes(selectedModel.size)}</p>
            </div>
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              className="p-1.5 rounded-md text-muted hover:text-white hover:bg-white/5"
              title="Replace"
              onClick={() => inputRef.current?.click()}
            >
              <RefreshCw size={14} />
            </button>
            <button
              className="p-1.5 rounded-md text-muted hover:text-error hover:bg-white/5"
              title="Remove"
              onClick={onClear}
            >
              <X size={14} />
            </button>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pth,.pt"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>
      )}
    </div>
  );
}
