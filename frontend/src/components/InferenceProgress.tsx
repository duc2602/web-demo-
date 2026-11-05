import { InferenceStatus } from "../types";
import { formatDuration } from "../utils/format";

const STATUS_LABEL: Record<string, string> = {
  queued: "Queued...",
  loading_model: "Loading model...",
  processing: "Running inference...",
  completed: "Completed",
  failed: "Failed",
};

export default function InferenceProgress({ status }: { status: InferenceStatus }) {
  const isFullImageProcessing =
    status.status === "processing" && status.total_tiles === 1 && status.processed_tiles === 0;
  const isIndeterminate =
    status.status === "queued" || status.status === "loading_model" || isFullImageProcessing;

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-medium text-white">
          {isFullImageProcessing ? "Processing full image..." : STATUS_LABEL[status.status]}
        </p>
        <span className="text-xs text-muted">{formatDuration(status.elapsed_seconds)}</span>
      </div>

      <div className="h-2 rounded-full bg-white/5 overflow-hidden">
        {isIndeterminate ? (
          <div className="inference-progress-indeterminate h-full w-1/3 rounded-full bg-accent" />
        ) : (
          <div
            className="h-full rounded-full bg-accent transition-all duration-300"
            style={{ width: `${status.progress}%` }}
          />
        )}
      </div>

      <div className="flex items-center justify-between mt-2 text-xs text-muted">
        <span>
          {isFullImageProcessing
            ? "Restoring full image"
            : status.total_tiles > 0
            ? `Processing tile ${status.processed_tiles} / ${status.total_tiles}`
            : status.status === "loading_model"
              ? "Loading model..."
              : status.status === "queued"
                ? "Waiting to start..."
                : "Preparing..."}
        </span>
        <span>{isIndeterminate ? " " : `${status.progress}%`}</span>
      </div>
    </div>
  );
}
