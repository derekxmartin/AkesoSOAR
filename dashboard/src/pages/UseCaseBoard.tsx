import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import usePageTitle from "../hooks/usePageTitle";
import api from "../lib/api";

interface UseCase {
  id: string;
  name: string;
  status: string;
  severity: string;
  owner_id: string;
  version: number;
}

const COLUMNS = ["draft", "testing", "production", "deprecated"] as const;
type Status = (typeof COLUMNS)[number];

const COLUMN_COLORS: Record<Status, string> = {
  draft: "border-slate-500",
  testing: "border-yellow-500",
  production: "border-green-500",
  deprecated: "border-red-500",
};

// Valid transitions from the lifecycle state machine
const VALID_TRANSITIONS: Record<string, string[]> = {
  draft: ["testing", "deprecated"],
  testing: ["production"],
  production: ["testing", "deprecated"],
  deprecated: [],
};

export default function UseCaseBoard() {
  usePageTitle("Use Case Board");
  const navigate = useNavigate();
  const { data, refetch } = useApiGet<{ items: UseCase[] }>(["use-cases-board"], "/use-cases", { limit: 200 });

  const [dragItem, setDragItem] = useState<UseCase | null>(null);
  const [dragOverCol, setDragOverCol] = useState<string | null>(null);
  const [confirmDialog, setConfirmDialog] = useState<{ uc: UseCase; target: Status } | null>(null);
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const [transitioning, setTransitioning] = useState(false);
  const reasonRef = useRef<HTMLInputElement>(null);

  const grouped: Record<Status, UseCase[]> = { draft: [], testing: [], production: [], deprecated: [] };
  for (const uc of data?.items || []) {
    const col = COLUMNS.includes(uc.status as Status) ? (uc.status as Status) : "draft";
    grouped[col].push(uc);
  }

  const handleDragStart = (uc: UseCase) => {
    setDragItem(uc);
  };

  const handleDragOver = (e: React.DragEvent, col: Status) => {
    e.preventDefault();
    setDragOverCol(col);
  };

  const handleDrop = (col: Status) => {
    setDragOverCol(null);
    if (!dragItem || dragItem.status === col) {
      setDragItem(null);
      return;
    }

    // Validate transition
    const allowed = VALID_TRANSITIONS[dragItem.status] || [];
    if (!allowed.includes(col)) {
      setError(`Cannot move from ${dragItem.status} to ${col}`);
      setTimeout(() => setError(""), 3000);
      setDragItem(null);
      return;
    }

    // Show confirmation dialog
    setConfirmDialog({ uc: dragItem, target: col });
    setReason("");
    setDragItem(null);
    setTimeout(() => reasonRef.current?.focus(), 100);
  };

  const handleTransition = async () => {
    if (!confirmDialog || !reason.trim()) return;
    setTransitioning(true);
    setError("");
    try {
      await api.post(`/use-cases/${confirmDialog.uc.id}/transition`, {
        to_status: confirmDialog.target,
        reason: reason.trim(),
      });
      setConfirmDialog(null);
      setReason("");
      refetch();
    } catch (err: any) {
      setError(err.response?.data?.detail || "Transition failed");
    } finally {
      setTransitioning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Use Case Board</h1>
        <span className="text-sm text-fg3">{data?.items?.length ?? 0} use cases · Drag to transition</span>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-2 rounded text-sm">
          {error}
        </div>
      )}

      {/* Kanban columns */}
      <div className="grid grid-cols-4 gap-4 min-h-[500px]">
        {COLUMNS.map((col) => (
          <div
            key={col}
            onDragOver={(e) => handleDragOver(e, col)}
            onDragLeave={() => setDragOverCol(null)}
            onDrop={() => handleDrop(col)}
            className={`rounded-lg border-t-4 ${COLUMN_COLORS[col]} bg-card-a border-x border-b border-edge p-3 transition-colors ${
              dragOverCol === col ? "bg-hover" : ""
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-fg capitalize">{col}</h3>
              <span className="text-xs text-fg4 bg-chip rounded-full px-2 py-0.5">{grouped[col].length}</span>
            </div>

            <div className="space-y-2">
              {grouped[col].map((uc) => (
                <div
                  key={uc.id}
                  draggable
                  onDragStart={() => handleDragStart(uc)}
                  onDragEnd={() => { setDragItem(null); setDragOverCol(null); }}
                  onClick={() => navigate(`/use-cases/${uc.id}`)}
                  className={`bg-card border border-edge rounded-lg p-3 cursor-grab active:cursor-grabbing hover:border-blue-500/50 transition-all ${
                    dragItem?.id === uc.id ? "opacity-50" : ""
                  }`}
                >
                  <div className="text-sm font-medium text-fg mb-1.5">{uc.name}</div>
                  <div className="flex items-center gap-2">
                    <Badge value={uc.severity} />
                    <span className="text-[10px] text-fg4">v{uc.version}</span>
                  </div>
                </div>
              ))}
              {grouped[col].length === 0 && (
                <div className="text-center text-fg4 text-xs py-8">
                  {dragOverCol === col ? "Drop here" : "No use cases"}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Confirmation dialog */}
      {confirmDialog && (
        <div className="fixed inset-0 bg-overlay flex items-center justify-center z-50">
          <div className="bg-card border border-edge rounded-xl shadow-2xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold text-fg mb-2">Confirm Transition</h2>
            <p className="text-sm text-fg2 mb-4">
              Move <strong>{confirmDialog.uc.name}</strong> from{" "}
              <Badge value={confirmDialog.uc.status} /> to <Badge value={confirmDialog.target} />
            </p>
            <div className="mb-4">
              <label className="block text-sm text-fg2 mb-1">Reason</label>
              <input
                ref={reasonRef}
                type="text"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleTransition()}
                placeholder="Why is this transitioning?"
                className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg placeholder-fg3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            {error && <p className="text-red-400 text-sm mb-3">{error}</p>}
            <div className="flex justify-end gap-2">
              <button
                onClick={() => { setConfirmDialog(null); setError(""); }}
                className="px-4 py-2 text-sm text-fg2 hover:text-fg"
              >
                Cancel
              </button>
              <button
                onClick={handleTransition}
                disabled={!reason.trim() || transitioning}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 text-white rounded text-sm font-medium"
              >
                {transitioning ? "Transitioning..." : "Confirm"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
