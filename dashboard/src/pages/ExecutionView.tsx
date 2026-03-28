import { ArrowLeft } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PlaybookGraph from "../components/PlaybookGraph";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";

interface StepResult {
  id: string;
  step_id: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  input_data: any;
  output_data: any;
  error: string | null;
  retry_count: number;
}

interface ExecutionDetail {
  id: string;
  playbook_id: string;
  playbook_version: number;
  trigger_alert_id: string | null;
  use_case_id: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  step_results: StepResult[];
  created_at: string;
}

export default function ExecutionView() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [selectedStepResult, setSelectedStepResult] = useState<StepResult | null>(null);

  const { data: execution, isLoading } = useApiGet<ExecutionDetail>(
    ["execution", id!],
    `/executions/${id}`
  );

  const { data: playbook } = useApiGet<any>(
    ["playbook", execution?.playbook_id || ""],
    `/playbooks/${execution?.playbook_id}`,
  );

  const stepStatuses = useMemo(() => {
    if (!execution?.step_results) return {};
    const map: Record<string, string> = {};
    for (const sr of execution.step_results) {
      map[sr.step_id] = sr.status;
    }
    return map;
  }, [execution]);

  if (isLoading || !execution) return <div className="text-fg3">Loading...</div>;

  const steps = playbook?.definition?.steps || [];

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("/executions")} className="text-fg3 hover:text-fg">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">Execution</h1>
          <p className="text-fg3 text-xs font-mono">{execution.id}</p>
        </div>
        <Badge value={execution.status} />
        {execution.duration_ms != null && (
          <span className="text-sm text-fg3">{execution.duration_ms}ms</span>
        )}
      </div>

      {/* Info bar */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-card-a rounded border border-edge p-3">
          <div className="text-xs text-fg3">Playbook</div>
          <div className="text-sm text-fg font-medium">{playbook?.name || execution.playbook_id.slice(0, 8)}</div>
        </div>
        <div className="bg-card-a rounded border border-edge p-3">
          <div className="text-xs text-fg3">Version</div>
          <div className="text-sm text-fg">v{execution.playbook_version}</div>
        </div>
        <div className="bg-card-a rounded border border-edge p-3">
          <div className="text-xs text-fg3">Alert</div>
          <div className="text-sm text-fg">{execution.trigger_alert_id || "manual"}</div>
        </div>
        <div className="bg-card-a rounded border border-edge p-3">
          <div className="text-xs text-fg3">Started</div>
          <div className="text-sm text-fg">{execution.started_at ? new Date(execution.started_at).toLocaleString() : "—"}</div>
        </div>
      </div>

      {/* DAG with execution colors */}
      {steps.length > 0 && (
        <PlaybookGraph
          steps={steps}
          stepStatuses={stepStatuses}
          onNodeClick={(stepId) => {
            const sr = execution.step_results.find((r) => r.step_id === stepId);
            setSelectedStepResult(sr || null);
          }}
        />
      )}

      {/* Step results timeline */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold mb-3">Step Results</h2>
        <div className="space-y-2">
          {execution.step_results.map((sr) => (
            <div
              key={sr.id}
              onClick={() => setSelectedStepResult(sr)}
              className={`flex items-center justify-between p-3 rounded border cursor-pointer transition-colors ${
                selectedStepResult?.id === sr.id
                  ? "bg-hover border-blue-500"
                  : "bg-card-a border-edge hover:bg-hover-row"
              }`}
            >
              <div className="flex items-center gap-3">
                <Badge value={sr.status} />
                <span className="text-sm font-medium text-fg">{sr.step_id}</span>
              </div>
              <div className="flex items-center gap-4 text-xs text-fg3">
                {sr.retry_count > 0 && <span>retries: {sr.retry_count}</span>}
                {sr.duration_ms != null && <span>{sr.duration_ms}ms</span>}
                {sr.error && <span className="text-red-400 max-w-48 truncate">{sr.error}</span>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Selected step detail */}
      {selectedStepResult && (
        <div className="mt-4 bg-card-a rounded-lg border border-edge p-4">
          <h3 className="text-sm font-semibold text-fg mb-3">
            Step: {selectedStepResult.step_id} — <Badge value={selectedStepResult.status} />
          </h3>
          <div className="grid grid-cols-2 gap-4">
            {selectedStepResult.input_data && (
              <div>
                <div className="text-xs text-fg3 mb-1">Input</div>
                <pre className="text-xs text-fg2 bg-nav rounded p-2 overflow-auto max-h-40">
                  {JSON.stringify(selectedStepResult.input_data, null, 2)}
                </pre>
              </div>
            )}
            {selectedStepResult.output_data && (
              <div>
                <div className="text-xs text-fg3 mb-1">Output</div>
                <pre className="text-xs text-fg2 bg-nav rounded p-2 overflow-auto max-h-40">
                  {JSON.stringify(selectedStepResult.output_data, null, 2)}
                </pre>
              </div>
            )}
          </div>
          {selectedStepResult.error && (
            <div className="mt-2">
              <div className="text-xs text-red-400 mb-1">Error</div>
              <pre className="text-xs text-red-300 bg-red-900/20 rounded p-2">{selectedStepResult.error}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
