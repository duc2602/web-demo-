import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAppContext } from "../context/AppContext";
import { Trash2, Boxes } from "lucide-react";
import { ModelMetadata } from "../types";
import { deleteModel, listModels } from "../services/modelService";
import { formatBytes } from "../utils/format";
import { useToast } from "../components/Toast";
import { extractErrorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Models() {
  const [models, setModels] = useState<ModelMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const { push } = useToast();
  const { workspace } = useAppContext();
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    refresh();
  }, []);

  async function refresh() {
    setLoading(true);
    try {
      setModels(await listModels());
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(id: string) {
    try {
      await deleteModel(id);
      setModels((prev) => prev.filter((m) => m.id !== id));
      if (workspace.selectedModel?.id === id) workspace.setSelectedModel(null);
      push("success", "Model deleted.");
    } catch (err) {
      push("error", extractErrorMessage(err, "Failed to delete model."));
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-8 py-8">
      <header className="mb-6">
        <h1 className="text-xl font-semibold text-white tracking-tight">Models</h1>
        <p className="text-sm text-muted mt-1">Manage uploaded model checkpoints</p>
      </header>

      {loading && <p className="text-sm text-muted">Loading...</p>}

      {!loading && models.length === 0 && (
        <div className="card flex flex-col items-center justify-center py-16 text-center">
          <Boxes size={22} className="text-muted mb-3" />
          <p className="text-sm text-white">No models yet</p>
          <p className="text-xs text-muted mt-1">Upload one from the Dashboard to get started.</p>
        </div>
      )}

      <div className="space-y-3">
        {models.map((m) => (
          <div key={m.id} className="card px-5 py-4 flex items-center justify-between">
            <div className="flex items-center gap-3 min-w-0">
              <span className="w-2 h-2 rounded-full bg-success shrink-0" />
              <div className="min-w-0">
                <p className="text-sm text-white truncate">{m.filename}</p>
                <p className="text-xs text-muted mt-0.5">{formatBytes(m.size)}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
              <span className="text-xs text-success capitalize">{m.status}</span>
              <button
                className="text-xs px-3 py-1.5 rounded-md border border-border text-white hover:bg-white/5"
                onClick={() => {
                  workspace.setSelectedModel(m);
                  push("success", `Đã chọn model "${m.filename}".`);
                  navigate("/");
                }}
              >
                Use
              </button>
              {user?.role === "admin" && (
                <button
                  className="p-2 rounded-md text-muted hover:text-error hover:bg-white/5"
                  onClick={() => handleDelete(m.id)}
                  title="Delete"
                  aria-label={`Delete ${m.filename}`}
                >
                  <Trash2 size={15} />
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
