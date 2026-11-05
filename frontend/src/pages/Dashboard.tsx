import { useEffect, useRef, useState } from "react";
import { Activity, Boxes, CheckCircle2, ChevronDown, Circle, Cpu, Loader2, Play, Sparkles } from "lucide-react";
import ModelUploader from "../components/ModelUploader";
import ImageUploader from "../components/ImageUploader";
import InferenceProgress from "../components/InferenceProgress";
import ResultViewer from "../components/ResultViewer";
import { useToast } from "../components/Toast";
import { ModelMetadata, SystemInfo } from "../types";
import { startInference, pollInference } from "../services/inferenceService";
import { listModels } from "../services/modelService";
import { api, extractErrorMessage } from "../services/api";
import { useAppContext } from "../context/AppContext";
import { useAuth } from "../context/AuthContext";
import { formatBytes } from "../utils/format";

export default function Dashboard() {
  const { settings, workspace } = useAppContext();
  const { user } = useAuth();
  const {
    selectedModel,
    setSelectedModel,
    imageFile,
    inputPreviewUrl,
    setImage,
    status,
    setStatus,
    running,
    setRunning,
  } = workspace;

  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [inferenceCount, setInferenceCount] = useState(0);
  const [system, setSystem] = useState<SystemInfo | null>(null);
  const modelPickerRef = useRef<HTMLDetailsElement>(null);
  const { push } = useToast();

  useEffect(() => {
      listModels()
      .then((list) => {
        setModels(list);
        // Model đang chọn đã bị xóa ở trang Models -> bỏ chọn để tránh chạy với model không còn tồn tại
        if (selectedModel && !list.some((m) => m.id === selectedModel.id)) {
          setSelectedModel(null);
        }
      })
      .catch(() => {});
    api.get("/api/system").then((r) => setSystem(r.data)).catch(() => {});
    api
      .get("/api/inference/history")
      .then((r) => setInferenceCount(r.data.length))
      .catch(() => {});
  }, []);

  

  async function handleRunInference() {
    if (!selectedModel || !imageFile) return;
    setRunning(true);
    setStatus(null);
    try {
      const { job_id } = await startInference(selectedModel.id, imageFile, settings);
      pollInference(job_id, (s) => {
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") {
          setRunning(false);
          if (s.status === "completed") {
            push("success", "Inference completed.");
            setInferenceCount((c) => c + 1);
          } else {
            push("error", s.error || "Inference failed.");
          }
        }
      });
    } catch (err) {
      setRunning(false);
      push("error", extractErrorMessage(err, "Failed to start inference."));
    }
  }

  const canRun = selectedModel !== null && imageFile !== null && !running;

  return (
    <div className="mx-auto max-w-7xl px-4 py-5 sm:px-8 sm:py-8">
      <header className="dashboard-hero mb-6 px-5 py-6 sm:mb-7 sm:px-8 sm:py-8">
        <div className="dashboard-hero-content flex flex-col justify-between gap-6 sm:flex-row sm:items-end">
          <div className="max-w-2xl">
            <span className="mb-4 inline-flex items-center gap-2 rounded-full border border-violet-300/15 bg-violet-300/[0.07] px-3 py-1.5 text-[11px] font-medium tracking-wide text-violet-200">
              <Sparkles size={13} aria-hidden="true" />
              KHÔI PHỤC ẢNH BẰNG AI
            </span>
            <h1 className="text-2xl font-semibold tracking-tight text-white sm:text-3xl">Khôi phục nét chữ, giữ trọn nội dung.</h1>
            <p className="mt-2 max-w-xl text-sm leading-relaxed text-zinc-400">
              Tải ảnh lên, chọn model và để AI làm rõ những nét chữ bị mờ hoặc hư hỏng.
            </p>
          </div>
          <div className="flex w-fit items-center gap-2 rounded-xl border border-white/[0.08] bg-black/20 px-3.5 py-2.5 text-xs text-zinc-300">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-30" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            {system ? `${system.device.toUpperCase()} SẴN SÀNG` : "ĐANG KIỂM TRA HỆ THỐNG"}
          </div>
        </div>
      </header>

      <div className="dashboard-stats mb-6 grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
        <StatCard label="Models" value={String(models.length)} icon={Boxes} />
        <StatCard label="Inferences" value={String(inferenceCount)} icon={Activity} />
        <StatCard label="Device" value={system ? system.device.toUpperCase() : "..."} icon={Cpu} />
      </div>

      <section className="dashboard-workspace grid items-start gap-4 lg:gap-5 xl:grid-cols-[minmax(0,1.55fr)_minmax(300px,0.85fr)]">
        <ImageUploader imageFile={imageFile} onImageSelected={(f) => setImage(f)} />

        <div className="flex flex-col gap-4">
          {!selectedModel && models.length > 0 && (
            <div className="card p-5">
              <div className="mb-3 flex items-center justify-between gap-3">
                <label className="text-sm font-medium text-white" htmlFor="model-picker">Choose a model</label>
                <span className="text-xs text-zinc-400">{models.length} available</span>
              </div>
              <details ref={modelPickerRef} className="model-picker relative">
                <summary id="model-picker" className="input flex cursor-pointer list-none items-center justify-between gap-3 py-3 text-sm">
                  <span className="truncate">Select an uploaded model...</span>
                  <ChevronDown size={16} className="shrink-0 text-zinc-400 transition-transform" />
                </summary>
                <div className="model-picker-menu absolute inset-x-0 top-full z-30 mt-2 max-h-64 overflow-y-auto rounded-lg border border-border p-1 shadow-2xl">
                  {models.map((model) => (
                    <button
                      key={model.id}
                      type="button"
                      role="option"
                      aria-selected={false}
                      className="flex w-full items-center justify-between gap-3 rounded-md px-3 py-2.5 text-left text-sm text-zinc-100 transition-colors hover:bg-white/[0.08] focus-visible:bg-white/[0.08] focus-visible:outline-none"
                      onClick={() => {
                        setSelectedModel(model);
                        if (modelPickerRef.current) modelPickerRef.current.open = false;
                      }}
                    >
                      <span className="min-w-0 truncate">{model.filename}</span>
                      <span className="shrink-0 text-xs text-zinc-400">{formatBytes(model.size)}</span>
                    </button>
                  ))}
                </div>
              </details>
              <p className="mt-2 text-xs text-zinc-400">Or upload a new model below.</p>
            </div>
          )}

          {user?.role === "admin" ? (
            <ModelUploader
              selectedModel={selectedModel}
              onModelReady={(m) => {
                setSelectedModel(m);
                setModels((prev) => [m, ...prev]);
              }}
              onClear={() => setSelectedModel(null)}
            />
          ) : models.length === 0 ? (
            <div className="card p-5">
              <p className="text-sm font-medium text-white">No shared models yet</p>
              <p className="mt-1 text-xs text-zinc-400">Ask an administrator to add a model.</p>
            </div>
          ) : null}

          <div className="card mt-auto p-5">
            <div className="mb-4">
              <p className="text-sm font-medium text-white">Inference setup</p>
              <p className="mt-1 text-xs text-zinc-400">Both a model and an input image are required.</p>
            </div>
            <div className="mb-5 space-y-2.5 border-t border-border pt-4">
              <SetupItem ready={selectedModel !== null} label={selectedModel ? selectedModel.filename : "Select or upload a model"} />
              <SetupItem ready={imageFile !== null} label={imageFile ? imageFile.name : "Choose an input image"} />
            </div>
            <button
              className={`btn-primary flex min-h-11 w-full items-center justify-center gap-2 px-5 py-3 text-sm font-semibold ${running ? "processing-glow" : ""}`}
              disabled={!canRun}
              onClick={handleRunInference}
            >
              {running ? (
                <>
                  <Loader2 size={17} className="animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Play size={17} />
                  Run Inference
                </>
              )}
            </button>
          </div>
        </div>
      </section>

      {status && status.status !== "completed" && status.status !== "failed" && (
        <div className="mt-5">
          <InferenceProgress status={status} />
        </div>
      )}

      {status && status.status === "completed" && inputPreviewUrl && (
        <div className="mt-5">
          <ResultViewer
            status={status}
            inputPreviewUrl={inputPreviewUrl}
            onUseAsInput={(file) => {
              setImage(file);
              document.querySelector(".app-main")?.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        </div>
      )}
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: typeof Boxes;
}) {
  return (
    <div className="stat-card card group relative flex min-h-[82px] items-center gap-3 overflow-hidden px-4 py-3">
      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-400/20 bg-slate-500/10 text-accent shadow-[0_0_24px_rgba(148,163,184,0.12)]">
        <Icon size={17} strokeWidth={1.8} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-muted">{label}</p>
        <p className="mt-1 truncate text-xl font-semibold text-white">{value}</p>
      </div>
    </div>
  );
}

function SetupItem({ ready, label }: { ready: boolean; label: string }) {
  const Icon = ready ? CheckCircle2 : Circle;
  return (
    <div className="flex min-w-0 items-center gap-2.5 text-sm">
      <Icon size={16} className={`shrink-0 ${ready ? "text-emerald-300" : "text-zinc-500"}`} aria-hidden="true" />
      <span className={`truncate ${ready ? "text-zinc-200" : "text-zinc-400"}`}>{label}</span>
    </div>
  );
}
