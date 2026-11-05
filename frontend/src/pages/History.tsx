import { useEffect, useState } from "react";
import { Clock3, History as HistoryIcon, ImageOff, Loader2, Trash2, X } from "lucide-react";
import { HistoryRecord } from "../types";
import { deleteHistory, getHistory, outputImageUrl } from "../services/inferenceService";
import { formatRelativeTime } from "../utils/format";
import { useToast } from "../components/Toast";

const DEGRADED_LABELS: Record<string, string> = {
  synthetic_noise: "Noisy input",
  blur: "Blurred input",
  broken: "Broken text",
  missing: "Missing regions",
  occlusion: "Occluded input",
};

export default function History() {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<HistoryRecord | null>(null);
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null);
  const { push } = useToast();

  useEffect(() => {
    getHistory()
      .then(setRecords)
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleDelete(record: HistoryRecord) {
    const confirmed = window.confirm(
      `Chuyển lượt chạy "${record.input_filename}" vào Thùng rác? Bạn có thể khôi phục sau.`
    );
    if (!confirmed) return;

    setDeletingJobId(record.job_id);
    try {
      await deleteHistory(record.job_id);
      setRecords((current) => current.filter((item) => item.job_id !== record.job_id));
      setSelectedRecord((current) => current?.job_id === record.job_id ? null : current);
      push("success", "Đã chuyển vào Thùng rác. Bạn có thể khôi phục bất cứ lúc nào.");
    } catch {
      push("error", "Không thể xóa lượt chạy. Vui lòng thử lại.");
    } finally {
      setDeletingJobId(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-7 sm:px-8 sm:py-9">
      <header className="mb-6">
        <p className="mb-2 text-xs font-medium text-accent">WORKSPACE / ACTIVITY</p>
        <h1 className="text-3xl font-semibold text-white">History</h1>
        <p className="mt-2 text-sm text-zinc-400">Open a run to review its input and output images.</p>
      </header>

      {loading && <p className="text-sm text-zinc-400">Loading runs...</p>}

      {!loading && records.length === 0 && (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <HistoryIcon size={22} className="mb-3 text-zinc-500" />
          <p className="text-sm text-white">No inference runs yet</p>
          <p className="mt-1 text-xs text-zinc-400">Completed runs will appear here.</p>
        </div>
      )}

      {!loading && records.length > 0 && (
        <div className="space-y-3">
          {records.map((record) => (
            <div
              key={record.job_id}
              className="card flex min-w-0 items-center gap-3 p-3 transition-colors hover:border-white/20 sm:gap-4 sm:p-4"
            >
              <button
                type="button"
                onClick={() => setSelectedRecord(record)}
                className="flex min-w-0 flex-1 items-center gap-4 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
              >
                <HistoryThumbnail record={record} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-sm font-medium text-white">{record.input_filename}</span>
                  <span className="mt-1 block truncate text-xs text-zinc-400">{record.model_filename}</span>
                </span>
                <span className="hidden shrink-0 text-right sm:block">
                  <span className="block text-xs text-zinc-300">
                    {record.processing_time_seconds ? `${record.processing_time_seconds}s` : "-"}
                  </span>
                  <span className="mt-1 block text-xs text-zinc-500">{formatRelativeTime(record.created_at)}</span>
                </span>
                <span className="shrink-0 text-xs text-zinc-400 sm:hidden">{formatRelativeTime(record.created_at)}</span>
              </button>
              <button
                type="button"
                title="Move run to Trash"
                aria-label={`Move ${record.input_filename} to Trash`}
                disabled={deletingJobId === record.job_id}
                onClick={() => void handleDelete(record)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 text-zinc-400 transition-colors hover:border-slate-300/30 hover:bg-slate-400/10 hover:text-slate-200 disabled:cursor-wait disabled:opacity-50"
              >
                {deletingJobId === record.job_id ? <Loader2 size={16} className="animate-spin" /> : <Trash2 size={16} />}
              </button>
            </div>
          ))}
        </div>
      )}

      {selectedRecord && (
        <RunDetails
          record={selectedRecord}
          onClose={() => setSelectedRecord(null)}
          onDelete={() => void handleDelete(selectedRecord)}
          deleting={deletingJobId === selectedRecord.job_id}
        />
      )}
    </div>
  );
}

function HistoryThumbnail({ record }: { record: HistoryRecord }) {
  const thumbnailUrl = record.input_id
    ? outputImageUrl(`/api/outputs/thumbnail/input/${record.input_id}`)
    : record.output_id
      ? outputImageUrl(`/api/outputs/thumbnail/${record.output_id}`)
      : null;

  return (
    <span className="flex h-14 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-black/30 sm:h-16 sm:w-20">
      {thumbnailUrl ? (
        <img src={thumbnailUrl} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" />
      ) : (
        <ImageOff size={18} className="text-zinc-500" aria-hidden="true" />
      )}
    </span>
  );
}

function RunDetails({
  record,
  onClose,
  onDelete,
  deleting,
}: {
  record: HistoryRecord;
  onClose: () => void;
  onDelete: () => void;
  deleting: boolean;
}) {
  const inputUrl = record.input_id
    ? outputImageUrl(`/api/outputs/input/${record.input_id}`)
    : null;
  const degradedUrl = record.degraded_id
    ? outputImageUrl(`/api/outputs/${record.degraded_id}`)
    : null;
  const outputUrl = record.output_id
    ? outputImageUrl(`/api/outputs/${record.output_id}`)
    : null;
  const outputIds = record.output_ids?.length
    ? record.output_ids
    : record.output_id
      ? [record.output_id]
      : [];

  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-3 backdrop-blur-sm sm:p-6"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section role="dialog" aria-modal="true" aria-labelledby="history-detail-title" className="card max-h-full w-full max-w-5xl overflow-y-auto p-4 shadow-2xl sm:p-6">
        <header className="mb-5 flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-xs font-medium text-accent">INFERENCE RUN</p>
            <h2 id="history-detail-title" className="mt-1 truncate text-lg font-semibold text-white">{record.input_filename}</h2>
            <p className="mt-1 truncate text-xs text-zinc-400">{record.model_filename}</p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close details" className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 text-zinc-300 hover:bg-white/[0.06]">
            <X size={17} />
          </button>
        </header>

        <div className="mb-5 flex flex-wrap gap-x-5 gap-y-2 border-y border-white/[0.08] py-3 text-xs text-zinc-300">
          <span className="inline-flex items-center gap-1.5"><Clock3 size={13} className="text-zinc-500" />{formatRelativeTime(record.created_at)}</span>
          <span>Processing time: {record.processing_time_seconds ? `${record.processing_time_seconds}s` : "-"}</span>
          <span>Status: {record.status}</span>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <HistoryImage title="Original input" imageUrl={inputUrl} />
          {degradedUrl && (
            <HistoryImage
              title={DEGRADED_LABELS[record.degradation_mode ?? ""] ?? "Degraded input"}
              imageUrl={degradedUrl}
            />
          )}
          {outputIds.length <= 1 ? (
            <HistoryImage title="Model output" imageUrl={outputUrl} />
          ) : (
            outputIds.map((outputId, index) => (
              <HistoryImage
                key={outputId}
                title={`Model output — page ${index + 1}`}
                imageUrl={outputImageUrl(`/api/outputs/${outputId}`)}
              />
            ))
          )}
        </div>

        {!inputUrl && (
          <p className="mt-4 rounded-lg border border-amber-300/15 bg-amber-300/[0.05] px-3 py-2.5 text-xs text-amber-100/80">
            This run predates image references in history, so its original input cannot be matched reliably. New runs will keep the original image here.
          </p>
        )}

        <footer className="mt-5 flex justify-end border-t border-white/[0.08] pt-4">
          <button
            type="button"
            onClick={onDelete}
            disabled={deleting}
            className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-slate-300/20 px-3.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-400/10 disabled:opacity-50"
          >
            {deleting ? <Loader2 size={15} className="animate-spin" /> : <Trash2 size={15} />}
            Move to Trash
          </button>
        </footer>
      </section>
    </div>
  );
}

function HistoryImage({ title, imageUrl }: { title: string; imageUrl: string | null }) {
  return (
    <figure className="min-w-0">
      <figcaption className="mb-2 text-xs font-medium text-zinc-300">{title}</figcaption>
      <div className="flex min-h-48 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-black/30 p-2 md:min-h-64">
        {imageUrl ? (
          <img src={imageUrl} alt={title} className="max-h-[55vh] max-w-full rounded object-contain" />
        ) : (
          <span className="text-xs text-zinc-500">Image unavailable</span>
        )}
      </div>
    </figure>
  );
}
