import { X } from "lucide-react";

interface Step {
  id: string;
  name: string;
  type: string;
  action?: { connector: string; operation: string; params?: Record<string, any> };
  condition?: { expression: string; branches: Record<string, string> };
  human_task?: { prompt: string; assignee_role: string; timeout_hours?: number };
  transform?: { expression: string; output_var?: string };
  parallel?: { branches: { steps: string[] }[]; join: string };
  on_success?: string;
  on_failure?: string;
  timeout_seconds?: number;
  retry?: { max_attempts: number; backoff_seconds: number };
}

interface Props {
  step: Step;
  onChange: (updated: Step) => void;
  onClose: () => void;
  onDelete: () => void;
  allStepIds: string[];
}

export default function StepConfigPanel({ step, onChange, onClose, onDelete, allStepIds }: Props) {
  const update = (path: string, value: any) => {
    const clone = JSON.parse(JSON.stringify(step));
    const keys = path.split(".");
    let obj = clone;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!obj[keys[i]]) obj[keys[i]] = {};
      obj = obj[keys[i]];
    }
    obj[keys[keys.length - 1]] = value;
    onChange(clone);
  };

  const field = (label: string, value: string, path: string, type: "text" | "textarea" | "number" = "text") => (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      {type === "textarea" ? (
        <textarea
          value={value || ""}
          onChange={(e) => update(path, e.target.value)}
          rows={2}
          className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      ) : (
        <input
          type={type}
          value={value || ""}
          onChange={(e) => update(path, type === "number" ? parseInt(e.target.value) || 0 : e.target.value)}
          className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      )}
    </div>
  );

  const stepSelect = (label: string, value: string, path: string) => (
    <div>
      <label className="block text-xs text-slate-400 mb-1">{label}</label>
      <select
        value={value || ""}
        onChange={(e) => update(path, e.target.value || undefined)}
        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white"
      >
        <option value="">None</option>
        <option value="abort">Abort</option>
        {allStepIds.filter((id) => id !== step.id).map((id) => (
          <option key={id} value={id}>{id}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="w-80 bg-slate-800 border-l border-slate-700 p-4 overflow-y-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-white">Step Configuration</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={16} /></button>
      </div>

      <div className="space-y-3">
        {field("Step ID", step.id, "id")}
        {field("Name", step.name, "name")}

        <div>
          <label className="block text-xs text-slate-400 mb-1">Type</label>
          <select
            value={step.type}
            onChange={(e) => update("type", e.target.value)}
            className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white"
          >
            {["action", "condition", "human_task", "transform", "parallel"].map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>

        {step.type === "action" && (
          <>
            {field("Connector", step.action?.connector || "", "action.connector")}
            {field("Operation", step.action?.operation || "", "action.operation")}
            {field("Params (JSON)", JSON.stringify(step.action?.params || {}), "action.params", "textarea")}
          </>
        )}

        {step.type === "condition" && (
          <>
            {field("Expression", step.condition?.expression || "", "condition.expression")}
            {stepSelect("True Branch", step.condition?.branches?.["true"] || "", "condition.branches.true")}
            {stepSelect("False Branch", step.condition?.branches?.["false"] || "", "condition.branches.false")}
          </>
        )}

        {step.type === "human_task" && (
          <>
            {field("Prompt", step.human_task?.prompt || "", "human_task.prompt", "textarea")}
            {field("Assignee Role", step.human_task?.assignee_role || "", "human_task.assignee_role")}
            {field("Timeout (hours)", String(step.human_task?.timeout_hours || 4), "human_task.timeout_hours", "number")}
          </>
        )}

        {step.type === "transform" && (
          <>
            {field("Expression", step.transform?.expression || "", "transform.expression", "textarea")}
            {field("Output Var", step.transform?.output_var || "", "transform.output_var")}
          </>
        )}

        <hr className="border-slate-700" />

        {stepSelect("On Success", step.on_success || "", "on_success")}
        {stepSelect("On Failure", step.on_failure || "", "on_failure")}
        {field("Timeout (seconds)", String(step.timeout_seconds || ""), "timeout_seconds", "number")}
        {field("Retry Max Attempts", String(step.retry?.max_attempts || ""), "retry.max_attempts", "number")}
        {field("Retry Backoff (seconds)", String(step.retry?.backoff_seconds || ""), "retry.backoff_seconds", "number")}

        <hr className="border-slate-700" />
        <button onClick={onDelete} className="w-full py-1.5 bg-red-600/20 text-red-400 border border-red-600/30 rounded text-xs hover:bg-red-600/30">
          Delete Step
        </button>
      </div>
    </div>
  );
}
