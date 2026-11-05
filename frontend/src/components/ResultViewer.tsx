import { Download, Copy, ExternalLink, ImagePlus } from "lucide-react";
import { useState } from "react";
import { InferenceStatus } from "../types";
import { outputImageUrl } from "../services/inferenceService";
import { useToast } from "./Toast";
import BeforeAfter from "./BeforeAfter";

interface Props {
  status: InferenceStatus;
  inputPreviewUrl: string;
  onUseAsInput: (file: File) => void;
}

export default function ResultViewer({ status, inputPreviewUrl, onUseAsInput }: Props) {
  const { push } = useToast();
  const [downloading, setDownloading] = useState(false);
  const [opening, setOpening] = useState(false);
  const [reusing, setReusing] = useState(false);
  const [comparisonSource, setComparisonSource] = useState<"clean" | "degraded">("clean");
  const [selectedPage, setSelectedPage] = useState(0);

  // Early return SAU khi đã gọi tất cả hooks (quy tắc React Hooks)
  if (status.status !== "completed" || !status.output_url) return null;

  const pages = status.pages ?? [];
  const activePageIndex = Math.min(selectedPage, Math.max(0, pages.length - 1));
  const page = pages[activePageIndex];
  const outputUrl = outputImageUrl(page?.output_url ?? status.output_url);
  const degradedPageUrl = page?.degraded_url ?? status.degraded_url;
  const degradedUrl = degradedPageUrl ? outputImageUrl(degradedPageUrl) : null;
  const metrics = page?.metrics ?? status.metrics;
  const confidenceScore = computeConfidenceScore(metrics);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(status.job_id);
      push("info", "Job ID copied.");
    } catch {
      push("error", "Failed to copy job ID.");
    }
  };

  // Download qua blob để ép đúng tên file, tránh bị cross-origin bỏ qua attribute `download`
  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (downloading) return;
    setDownloading(true);
    try {
      const res = await fetch(outputUrl, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `output-${status.job_id}${pages.length > 1 ? `-page-${activePageIndex + 1}` : ""}.png`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      push("error", "Download failed. Please try again.");
    } finally {
      setDownloading(false);
    }
  };

  const handleUseAsInput = async () => {
    if (reusing) return;
    setReusing(true);
    try {
      const res = await fetch(outputUrl, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const file = new File([blob], `output-${status.job_id}${pages.length > 1 ? `-page-${activePageIndex + 1}` : ""}.png`, {
        type: blob.type || "image/png",
      });
      onUseAsInput(file);
      push("success", "Output selected as the next input image.");
    } catch {
      push("error", "Could not reuse the output. Please try again.");
    } finally {
      setReusing(false);
    }
  };

  // Open qua blob để ép browser hiển thị inline thay vì tải về
  const handleOpen = async (e: React.MouseEvent) => {
    e.preventDefault();
    if (opening) return;
    setOpening(true);
    try {
      const res = await fetch(outputUrl, { credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      window.open(url, "_blank", "noopener,noreferrer");
      // Giải phóng blob URL sau 60s để tab mới kịp load
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      push("error", "Failed to open image.");
    } finally {
      setOpening(false);
    }
  };

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm font-medium text-white tracking-tight">Result</p>
        <button
          type="button"
          className="flex items-center gap-1.5 text-xs text-muted hover:text-white"
          onClick={handleCopy}
        >
          <Copy size={12} aria-hidden="true" />
          Copy job ID
        </button>
      </div>

      {degradedUrl && pages.length <= 1 && (
        <div role="group" aria-label="Select comparison input" className="mb-3 inline-flex rounded-lg border border-white/10 bg-black/20 p-1">
          <button
            type="button"
            aria-pressed={comparisonSource === "clean"}
            onClick={() => setComparisonSource("clean")}
            className={`rounded-md px-3 py-1.5 text-xs transition-colors ${comparisonSource === "clean" ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"}`}
          >
            Clean reference
          </button>
          <button
            type="button"
            aria-pressed={comparisonSource === "degraded"}
            onClick={() => setComparisonSource("degraded")}
            className={`rounded-md px-3 py-1.5 text-xs transition-colors ${comparisonSource === "degraded" ? "bg-white/10 text-white" : "text-zinc-400 hover:text-white"}`}
          >
            Degraded input
          </button>
        </div>
      )}

      {pages.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-2" role="group" aria-label="Select document page">
          {pages.map((resultPage, index) => (
            <button
              key={resultPage.output_id}
              type="button"
              aria-pressed={activePageIndex === index}
              onClick={() => setSelectedPage(index)}
              className={`rounded-lg border px-3 py-1.5 text-xs ${activePageIndex === index ? "border-accent/50 bg-accent/10 text-white" : "border-white/10 text-zinc-400 hover:text-white"}`}
            >
              Page {index + 1}
            </button>
          ))}
        </div>
      )}

      {pages.length > 1 ? (
        <div className="flex min-h-64 items-center justify-center overflow-hidden rounded-xl border border-white/10 bg-black/30 p-2">
          <img src={outputUrl} alt={`Restored page ${activePageIndex + 1}`} className="max-h-[65vh] max-w-full object-contain" />
        </div>
      ) : (
        <BeforeAfter
          beforeUrl={comparisonSource === "degraded" && degradedUrl ? degradedUrl : inputPreviewUrl}
          afterUrl={outputUrl}
          beforeLabel={degradedUrl ? (comparisonSource === "degraded" ? "DEGRADED INPUT" : "CLEAN REFERENCE") : "INPUT"}
          afterLabel="OUTPUT"
        />
      )}

      <div className="mt-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">AI Metrics</p>
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Stat
            label="Inference Time"
            value={
              status.processing_time_seconds !== null && status.processing_time_seconds !== undefined
                ? formatProcessingTime(status.processing_time_seconds)
                : "-"
            }
          />
          <Stat
            label="Confidence Score"
            value={confidenceScore !== null ? `${confidenceScore.toFixed(1)}%` : "N/A"}
          />
          <Stat
            label="Input"
            value={
              page?.input ?? status.input
              ? `${(page?.input ?? status.input)!.width} × ${(page?.input ?? status.input)!.height}`
                : "-"
            }
          />
          <Stat
            label="Output"
            value={
              page?.output ?? status.output
              ? `${(page?.output ?? status.output)!.width} × ${(page?.output ?? status.output)!.height}`
                : "-"
            }
          />
        </div>
      </div>

      {metrics && (
        <div className="grid grid-cols-2 gap-3 mt-3">
          <Stat
            label="PSNR vs input"
            value={`${metrics.psnr_vs_input.toFixed(2)} dB`}
          />
          <Stat
            label="SSIM vs input"
            value={metrics.ssim_vs_input.toFixed(4)}
          />
          {metrics.psnr_vs_ground_truth !== null && (
            <Stat
              label="PSNR vs clean reference"
              value={`${metrics.psnr_vs_ground_truth.toFixed(2)} dB`}
            />
          )}
          {metrics.ssim_vs_ground_truth !== null && (
            <Stat
              label="SSIM vs clean reference"
              value={metrics.ssim_vs_ground_truth.toFixed(4)}
            />
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-2 mt-5">
        <button
          type="button"
          onClick={handleDownload}
          disabled={downloading}
          className="btn-primary flex min-w-40 flex-1 items-center justify-center gap-2 py-2.5 text-sm disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Download size={16} aria-hidden="true" />
          {downloading ? "Downloading..." : "Download Output"}
        </button>

        <button
          type="button"
          onClick={() => void handleUseAsInput()}
          disabled={reusing}
          className="flex items-center justify-center gap-2 rounded-lg border border-border px-3 py-2.5 text-sm text-white transition-colors hover:bg-white/5 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <ImagePlus size={16} aria-hidden="true" />
          {reusing ? "Preparing..." : "Use as input"}
        </button>

        <button
          type="button"
          onClick={handleOpen}
          disabled={opening}
          aria-label="Open output in new tab"
          className="flex items-center justify-center gap-2 py-2.5 px-4 text-sm rounded-lg border border-border text-white hover:bg-white/5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <ExternalLink size={16} aria-hidden="true" />
          {opening ? "Opening..." : "Open in new tab"}
        </button>
      </div>
    </div>
  );
}

function computeConfidenceScore(metrics: { psnr_vs_input: number; ssim_vs_input: number; psnr_vs_ground_truth: number | null; ssim_vs_ground_truth: number | null } | null): number | null {
  if (!metrics) return null;

  const psnr = metrics.psnr_vs_ground_truth ?? metrics.psnr_vs_input;
  const ssim = metrics.ssim_vs_ground_truth ?? metrics.ssim_vs_input;
  const psnrRatio = Math.min(psnr / 40, 1) * 100;
  const ssimRatio = Math.min(ssim * 100, 100);
  const confidence = (psnrRatio * 0.55) + (ssimRatio * 0.45);

  return Math.max(0, Math.min(confidence, 100));
}

function formatProcessingTime(seconds: number): string {
  if (seconds < 1) {
    return `${(seconds * 1000).toFixed(0)} ms`;
  }

  return `${seconds.toFixed(2)} s`;
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-white/[0.03] rounded-lg px-3 py-2.5">
      <p className="text-[10px] text-muted mb-0.5">{label}</p>
      <p className="text-sm text-white">{value}</p>
    </div>
  );
}