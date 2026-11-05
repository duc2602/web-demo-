import { useEffect, useState } from "react";
import { ImageOff, RotateCcw, Trash2 } from "lucide-react";
import { HistoryRecord } from "../types";
import { getTrash, outputImageUrl, permanentlyDeleteHistory, restoreHistory } from "../services/inferenceService";
import { formatRelativeTime } from "../utils/format";
import { useToast } from "../components/Toast";
import { useAuth } from "../context/AuthContext";

export default function Trash() {
  const [records, setRecords] = useState<HistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyJobId, setBusyJobId] = useState<string | null>(null);
  const { push } = useToast();
  const { user } = useAuth();

  useEffect(() => {
    getTrash()
      .then(setRecords)
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, []);

  async function handleRestore(record: HistoryRecord) {
    setBusyJobId(record.job_id);
    try {
      await restoreHistory(record.job_id);
      setRecords((current) => current.filter((item) => item.job_id !== record.job_id));
      push("success", "Đã khôi phục lượt chạy về History.");
    } catch {
      push("error", "Không thể khôi phục lượt chạy. Vui lòng thử lại.");
    } finally {
      setBusyJobId(null);
    }
  }

  async function handlePermanentDelete(record: HistoryRecord) {
    const confirmed = window.confirm(
      `Xóa vĩnh viễn lượt chạy "${record.input_filename}" và các ảnh liên quan? Không thể khôi phục thao tác này.`
    );
    if (!confirmed) return;

    setBusyJobId(record.job_id);
    try {
      await permanentlyDeleteHistory(record.job_id);
      setRecords((current) => current.filter((item) => item.job_id !== record.job_id));
      push("success", "Đã xóa vĩnh viễn lượt chạy và ảnh liên quan.");
    } catch {
      push("error", "Không thể xóa lượt chạy. Vui lòng thử lại.");
    } finally {
      setBusyJobId(null);
    }
  }

  return (
    <div className="mx-auto max-w-6xl px-5 py-7 sm:px-8 sm:py-9">
      <header className="mb-6">
        <p className="mb-2 text-xs font-medium text-accent">WORKSPACE / RECOVERY</p>
        <h1 className="text-3xl font-semibold text-white">Thùng rác</h1>
        <p className="mt-2 text-sm text-zinc-400">Khôi phục lượt chạy về History hoặc xóa vĩnh viễn cùng ảnh đã lưu.</p>
      </header>

      {loading && <p className="text-sm text-zinc-400">Đang tải...</p>}

      {!loading && records.length === 0 && (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <Trash2 size={22} className="mb-3 text-zinc-500" />
          <p className="text-sm text-white">Thùng rác đang trống</p>
          <p className="mt-1 text-xs text-zinc-400">Các lượt bạn chuyển khỏi History sẽ xuất hiện ở đây.</p>
        </div>
      )}

      {!loading && records.length > 0 && (
        <div className="space-y-3">
          {records.map((record) => (
            <div key={record.job_id} className="card flex min-w-0 items-center gap-3 p-3 sm:gap-4 sm:p-4">
              <TrashThumbnail record={record} />
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-white">{record.input_filename}</p>
                <p className="mt-1 truncate text-xs text-zinc-400">{record.model_filename}</p>
                <p className="mt-1 text-xs text-zinc-500">Đã chuyển {record.deleted_at ? formatRelativeTime(record.deleted_at) : "vào thùng rác"}</p>
              </div>
              <button
                type="button"
                title="Khôi phục"
                aria-label={`Khôi phục ${record.input_filename}`}
                disabled={busyJobId === record.job_id}
                onClick={() => void handleRestore(record)}
                className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-emerald-300/20 text-emerald-200 transition-colors hover:bg-emerald-300/10 disabled:opacity-50"
              >
                <RotateCcw size={16} />
              </button>
              {user?.role === "admin" && (
                <button
                  type="button"
                  title="Xóa vĩnh viễn"
                  aria-label={`Xóa vĩnh viễn ${record.input_filename}`}
                  disabled={busyJobId === record.job_id}
                  onClick={() => void handlePermanentDelete(record)}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-300/20 text-slate-200 transition-colors hover:bg-slate-400/10 disabled:opacity-50"
                >
                  <Trash2 size={16} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TrashThumbnail({ record }: { record: HistoryRecord }) {
  const imageUrl = record.input_id
    ? outputImageUrl(`/api/outputs/thumbnail/input/${record.input_id}`)
    : (record.output_ids?.[0] ?? record.output_id)
      ? outputImageUrl(`/api/outputs/thumbnail/${record.output_ids?.[0] ?? record.output_id}`)
      : null;

  return (
    <div className="flex h-14 w-16 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-white/10 bg-black/30 sm:h-16 sm:w-20">
      {imageUrl ? (
        <img src={imageUrl} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" />
      ) : (
        <ImageOff size={18} className="text-zinc-500" aria-hidden="true" />
      )}
    </div>
  );
}