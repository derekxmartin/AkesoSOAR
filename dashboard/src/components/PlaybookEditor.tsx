import * as yaml from "js-yaml";
import { Download, Plus, Upload } from "lucide-react";
import { useCallback, useState } from "react";
import PlaybookGraph from "./PlaybookGraph";
import StepConfigPanel from "./StepConfigPanel";

interface Step {
  id: string;
  name: string;
  type: string;
  action?: any;
  condition?: any;
  human_task?: any;
  transform?: any;
  parallel?: any;
  on_success?: string;
  on_failure?: string;
  timeout_seconds?: number;
  retry?: { max_attempts: number; backoff_seconds: number };
}

interface Props {
  initialSteps: Step[];
  onChange: (steps: Step[]) => void;
}

const STEP_TEMPLATES: Record<string, Partial<Step>> = {
  action: { type: "action", action: { connector: "", operation: "", params: {} } },
  condition: { type: "condition", condition: { expression: "", branches: { true: "", false: "" } } },
  human_task: { type: "human_task", human_task: { prompt: "", assignee_role: "soc_l2", timeout_hours: 4 } },
  transform: { type: "transform", transform: { expression: "", output_var: "" } },
  parallel: { type: "parallel", parallel: { branches: [{ steps: [] }], join: "all" } },
};

export default function PlaybookEditor({ initialSteps, onChange }: Props) {
  const [steps, setSteps] = useState<Step[]>(initialSteps);
  const [selectedStepId, setSelectedStepId] = useState<string | null>(null);
  const [yamlInput, setYamlInput] = useState("");
  const [showImport, setShowImport] = useState(false);


  const updateSteps = useCallback(
    (newSteps: Step[]) => {
      setSteps(newSteps);
      onChange(newSteps);
    },
    [onChange]
  );

  const addStep = (type: string) => {
    const count = steps.filter((s) => s.type === type).length + 1;
    const id = `${type}_${count}`;
    const newStep: Step = {
      id,
      name: `New ${type} ${count}`,
      ...STEP_TEMPLATES[type],
    } as Step;
    updateSteps([...steps, newStep]);
    setSelectedStepId(id);
  };

  const updateStep = (updated: Step) => {
    const idx = steps.findIndex((s) => s.id === selectedStepId);
    if (idx === -1) return;
    const newSteps = [...steps];
    newSteps[idx] = updated;
    if (updated.id !== selectedStepId) {
      for (const s of newSteps) {
        if (s.on_success === selectedStepId) s.on_success = updated.id;
        if (s.on_failure === selectedStepId) s.on_failure = updated.id;
      }
      setSelectedStepId(updated.id);
    }
    updateSteps(newSteps);
  };

  const deleteStep = () => {
    if (!selectedStepId) return;
    updateSteps(steps.filter((s) => s.id !== selectedStepId));
    setSelectedStepId(null);
  };

  const handleEdgeConnect = useCallback(
    (sourceId: string, targetId: string, sourceHandle?: string) => {
      const newSteps = steps.map((s) => {
        if (s.id !== sourceId) return s;
        const clone = { ...s };
        if (s.type === "condition" && sourceHandle) {
          clone.condition = {
            ...clone.condition,
            branches: { ...clone.condition?.branches, [sourceHandle]: targetId },
          };
        } else {
          clone.on_success = targetId;
        }
        return clone;
      });
      updateSteps(newSteps);
    },
    [steps, updateSteps]
  );

  const exportYaml = () => {
    const doc = { name: "Playbook", steps };
    const yamlStr = yaml.dump(doc, { lineWidth: 120, noRefs: true });
    const blob = new Blob([yamlStr], { type: "text/yaml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "playbook.yaml";
    a.click();
    URL.revokeObjectURL(url);
  };

  const importYaml = () => {
    try {
      const parsed = yaml.load(yamlInput) as any;
      if (parsed?.steps && Array.isArray(parsed.steps)) {
        updateSteps(parsed.steps);
        setShowImport(false);
        setYamlInput("");
      }
    } catch {
      // Invalid YAML
    }
  };

  const selectedStep = steps.find((s) => s.id === selectedStepId);

  return (
    <div className="flex flex-col gap-4">
      {/* Toolbar */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-fg3 mr-2">Add step:</span>
        {Object.keys(STEP_TEMPLATES).map((type) => (
          <button
            key={type}
            onClick={() => addStep(type)}
            className="flex items-center gap-1 px-3 py-1.5 bg-inset hover:bg-hover border border-edge2 rounded text-xs font-medium transition-colors"
          >
            <Plus size={12} /> {type}
          </button>
        ))}

        <div className="flex-1" />

        <button onClick={exportYaml} className="flex items-center gap-1 px-3 py-1.5 bg-inset hover:bg-hover border border-edge2 rounded text-xs">
          <Download size={12} /> Export YAML
        </button>
        <button onClick={() => setShowImport(!showImport)} className="flex items-center gap-1 px-3 py-1.5 bg-inset hover:bg-hover border border-edge2 rounded text-xs">
          <Upload size={12} /> Import YAML
        </button>
      </div>

      {showImport && (
        <div className="bg-card border border-edge rounded-lg p-4 space-y-2">
          <textarea
            value={yamlInput}
            onChange={(e) => setYamlInput(e.target.value)}
            rows={8}
            placeholder="Paste playbook YAML here..."
            className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-xs text-fg font-mono placeholder-fg3 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <button onClick={importYaml} className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-xs font-medium text-white">
            Import
          </button>
        </div>
      )}

      {/* Graph + Config Panel */}
      <div className="flex gap-0">
        <div className="flex-1">
          <PlaybookGraph
            steps={steps}
            onNodeClick={(id) => setSelectedStepId(id)}
            onEdgeConnect={handleEdgeConnect}
            interactive
          />
        </div>
        {selectedStep && (
          <StepConfigPanel
            step={selectedStep}
            onChange={updateStep}
            onClose={() => setSelectedStepId(null)}
            onDelete={deleteStep}
            allStepIds={steps.map((s) => s.id)}
          />
        )}
      </div>

      <div className="text-xs text-fg4">
        {steps.length} step(s) | Click a node to configure | Drag nodes to reposition
      </div>
    </div>
  );
}
