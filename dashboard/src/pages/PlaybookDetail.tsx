import { ArrowLeft, Edit, Play } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PlaybookGraph from "../components/PlaybookGraph";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import api from "../lib/api";

export default function PlaybookDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: pb, isLoading } = useApiGet<any>(["playbook", id!], `/playbooks/${id}`);
  const [selectedStep, setSelectedStep] = useState<any>(null);
  const [executing, setExecuting] = useState(false);

  const handleExecute = async () => {
    setExecuting(true);
    try {
      const { data } = await api.post(`/playbooks/${id}/execute`, { alert_payload: {} });
      navigate(`/executions/${data.id}`);
    } catch {
      setExecuting(false);
    }
  };

  if (isLoading || !pb) return <div className="text-slate-400">Loading...</div>;

  const steps = pb.definition?.steps || [];

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("/playbooks")} className="text-slate-400 hover:text-white">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{pb.name}</h1>
          <p className="text-slate-400 text-sm">{pb.description}</p>
        </div>
        <Badge value={pb.enabled ? "production" : "deprecated"} />
        <Badge value={pb.trigger_type} />
        <span className="text-sm text-slate-400">v{pb.version}</span>
        <button
          onClick={() => navigate(`/playbooks/${id}/edit`)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm"
        >
          <Edit size={14} /> Edit
        </button>
        <button
          onClick={handleExecute}
          disabled={executing || !pb.enabled}
          className="flex items-center gap-2 px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:bg-slate-700 rounded text-sm"
        >
          <Play size={14} /> Execute
        </button>
      </div>

      {/* DAG Visualization */}
      {steps.length > 0 ? (
        <PlaybookGraph steps={steps} onNodeClick={(_stepId, step) => setSelectedStep(step)} />
      ) : (
        <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-12 text-center text-slate-400">
          No steps defined
        </div>
      )}

      {/* Step detail panel */}
      {selectedStep && (
        <div className="mt-4 bg-slate-800/50 rounded-lg border border-slate-700 p-4">
          <h3 className="text-sm font-semibold text-white mb-2">Step: {selectedStep.name}</h3>
          <pre className="text-xs text-slate-300 overflow-auto max-h-48">
            {JSON.stringify(selectedStep, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
