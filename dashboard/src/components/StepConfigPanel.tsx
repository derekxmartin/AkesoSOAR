import { useEffect, useState } from "react";
import { X } from "lucide-react";
import api from "../lib/api";
import { FieldLabel } from "./Tooltip";

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

interface ConnectorInfo {
  name: string;
  display_name: string;
  connector_type: string;
  enabled: boolean;
  operations: Record<string, { description?: string; method?: string; path?: string; service?: string; params_schema?: Record<string, any> }>;
}

interface Props {
  step: Step;
  onChange: (updated: Step) => void;
  onClose: () => void;
  onDelete: () => void;
  allStepIds: string[];
}

/* ── tooltip text for every field ── */
const TIPS = {
  stepId: "Unique identifier for this step. Used in on_success/on_failure routing and Jinja2 references like {{ steps.<id>.result }}.",
  name: "Human-readable label displayed on the graph node. Does not affect execution.",
  type: "Determines what this step does: action (call a connector), condition (branch on expression), human_task (wait for manual approval), transform (reshape data), or parallel (run branches concurrently).",
  connector: "The integration this step calls. Each connector represents an Akeso product or external service (SIEM, EDR, Firewall, etc.).",
  operation: "The specific action to invoke on the selected connector. Available operations depend on the connector chosen above.",
  params: "Input values passed to the operation. Use Jinja2 templates like {{ alert.source_ip }} or {{ steps.prev_step.result.field }} to reference dynamic data.",
  expression: "A Jinja2 expression that evaluates to true or false. Example: {{ alert.severity == 'critical' }} or {{ steps.enrich.result.score > 7 }}.",
  trueBranch: "The step to execute when the condition evaluates to true.",
  falseBranch: "The step to execute when the condition evaluates to false.",
  prompt: "The message shown to the analyst when this step is reached. Should clearly describe what action or decision is needed.",
  assigneeRole: "The SOC role that can approve this task. Only users with this role will see it in their pending tasks queue.",
  timeoutHours: "Hours to wait for approval before the step times out. After timeout, the on_failure path is taken.",
  transformExpr: "A Jinja2 expression that reshapes or extracts data. The result is stored in the output variable. Example: {{ steps.enrich.result.indicators | selectattr('malicious') | list }}.",
  outputVar: "Variable name to store the transform result. Access it in later steps as {{ steps.<step_id>.result.<output_var> }}.",
  onSuccess: "The next step to execute when this step completes successfully. Select 'None' to end the playbook, or 'Abort' to stop with an error.",
  onFailure: "The step to execute if this step fails (error, timeout, or rejection). Useful for rollback or escalation flows.",
  timeout: "Maximum seconds this step can run before it's considered failed. The on_failure path is taken after timeout. Leave empty for no limit.",
  retryMax: "Number of times to retry this step on failure before giving up. Set to 0 or leave empty for no retries.",
  retryBackoff: "Seconds to wait between retry attempts. Each retry waits this long before trying again.",
};

export default function StepConfigPanel({ step, onChange, onClose, onDelete, allStepIds }: Props) {
  const [connectors, setConnectors] = useState<ConnectorInfo[]>([]);
  const [loadingConnectors, setLoadingConnectors] = useState(false);

  useEffect(() => {
    setLoadingConnectors(true);
    api.get("/connectors").then((r) => setConnectors(r.data)).catch(() => {}).finally(() => setLoadingConnectors(false));
  }, []);

  const selectedConnector = connectors.find((c) => c.name === step.action?.connector);
  const availableOps = selectedConnector ? Object.keys(selectedConnector.operations) : [];
  const selectedOp = selectedConnector?.operations[step.action?.operation || ""];

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

  const field = (label: string, tooltip: string, value: string, path: string, type: "text" | "textarea" | "number" = "text") => (
    <div>
      <FieldLabel label={label} tooltip={tooltip} />
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

  const stepSelect = (label: string, tooltip: string, value: string, path: string) => (
    <div>
      <FieldLabel label={label} tooltip={tooltip} />
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

  const connectorSelect = () => (
    <div>
      <FieldLabel label="Connector" tooltip={TIPS.connector} />
      <select
        value={step.action?.connector || ""}
        onChange={(e) => {
          update("action.connector", e.target.value);
          update("action.operation", "");
        }}
        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white"
      >
        <option value="">Select a connector...</option>
        {connectors.map((c) => (
          <option key={c.name} value={c.name}>
            {c.display_name} ({c.connector_type})
          </option>
        ))}
      </select>
      {loadingConnectors && <p className="text-[10px] text-slate-500 mt-0.5">Loading connectors...</p>}
    </div>
  );

  const operationSelect = () => (
    <div>
      <FieldLabel label="Operation" tooltip={TIPS.operation} />
      <select
        value={step.action?.operation || ""}
        onChange={(e) => {
          const opName = e.target.value;
          update("action.operation", opName);
          if (opName && selectedConnector) {
            const op = selectedConnector.operations[opName];
            if (op?.params_schema) {
              const template: Record<string, string> = {};
              for (const key of Object.keys(op.params_schema)) {
                template[key] = `{{ ${key} }}`;
              }
              update("action.params", template);
            }
          }
        }}
        disabled={!selectedConnector}
        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white disabled:opacity-50"
      >
        <option value="">{selectedConnector ? "Select an operation..." : "Select a connector first"}</option>
        {availableOps.map((op) => (
          <option key={op} value={op}>{op}</option>
        ))}
      </select>
      {selectedOp?.description && (
        <p className="text-[10px] text-slate-500 mt-0.5">{selectedOp.description}</p>
      )}
      {selectedOp?.method && selectedOp?.path && (
        <p className="text-[10px] text-blue-400 mt-0.5">{selectedOp.method} {selectedOp.path}</p>
      )}
      {selectedOp?.service && (
        <p className="text-[10px] text-blue-400 mt-0.5">gRPC: {selectedOp.service}</p>
      )}
    </div>
  );

  const paramsEditor = () => {
    const paramKeys = selectedOp?.params_schema ? Object.keys(selectedOp.params_schema) : [];
    const currentParams = step.action?.params || {};

    if (paramKeys.length > 0) {
      return (
        <div>
          <FieldLabel label="Parameters" tooltip={TIPS.params} />
          <div className="space-y-1.5 bg-slate-750 rounded p-2 border border-slate-600">
            {paramKeys.map((key) => {
              const schema = selectedOp!.params_schema![key];
              const desc = typeof schema === "object" ? schema.description : schema;
              return (
                <div key={key}>
                  <label className="block text-[10px] text-slate-400">
                    {key}
                    {desc && <span className="ml-1 text-slate-500">— {desc}</span>}
                  </label>
                  <input
                    type="text"
                    value={currentParams[key] ?? ""}
                    onChange={(e) => {
                      const updated = { ...currentParams, [key]: e.target.value };
                      update("action.params", updated);
                    }}
                    placeholder={`{{ alert.${key} }}`}
                    className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              );
            })}
          </div>
          <p className="text-[10px] text-slate-500 mt-1">Use Jinja2 syntax for dynamic values</p>
        </div>
      );
    }

    return field("Params (JSON)", TIPS.params, JSON.stringify(currentParams, null, 2), "action.params", "textarea");
  };

  const roleSelect = () => (
    <div>
      <FieldLabel label="Assignee Role" tooltip={TIPS.assigneeRole} />
      <select
        value={step.human_task?.assignee_role || ""}
        onChange={(e) => update("human_task.assignee_role", e.target.value)}
        className="w-full px-2 py-1 bg-slate-700 border border-slate-600 rounded text-xs text-white"
      >
        <option value="">Select a role...</option>
        {["admin", "soc_l1", "soc_l2", "soc_l3", "ir_lead"].map((r) => (
          <option key={r} value={r}>{r}</option>
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
        {field("Step ID", TIPS.stepId, step.id, "id")}
        {field("Name", TIPS.name, step.name, "name")}

        <div>
          <FieldLabel label="Type" tooltip={TIPS.type} />
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
            {connectorSelect()}
            {operationSelect()}
            {paramsEditor()}
          </>
        )}

        {step.type === "condition" && (
          <>
            {field("Expression", TIPS.expression, step.condition?.expression || "", "condition.expression")}
            {stepSelect("True Branch", TIPS.trueBranch, step.condition?.branches?.["true"] || "", "condition.branches.true")}
            {stepSelect("False Branch", TIPS.falseBranch, step.condition?.branches?.["false"] || "", "condition.branches.false")}
          </>
        )}

        {step.type === "human_task" && (
          <>
            {field("Prompt", TIPS.prompt, step.human_task?.prompt || "", "human_task.prompt", "textarea")}
            {roleSelect()}
            {field("Timeout (hours)", TIPS.timeoutHours, String(step.human_task?.timeout_hours || 4), "human_task.timeout_hours", "number")}
          </>
        )}

        {step.type === "transform" && (
          <>
            {field("Expression", TIPS.transformExpr, step.transform?.expression || "", "transform.expression", "textarea")}
            {field("Output Var", TIPS.outputVar, step.transform?.output_var || "", "transform.output_var")}
          </>
        )}

        <hr className="border-slate-700" />

        {stepSelect("On Success", TIPS.onSuccess, step.on_success || "", "on_success")}
        {stepSelect("On Failure", TIPS.onFailure, step.on_failure || "", "on_failure")}
        {field("Timeout (seconds)", TIPS.timeout, String(step.timeout_seconds || ""), "timeout_seconds", "number")}
        {field("Retry Max Attempts", TIPS.retryMax, String(step.retry?.max_attempts || ""), "retry.max_attempts", "number")}
        {field("Retry Backoff (seconds)", TIPS.retryBackoff, String(step.retry?.backoff_seconds || ""), "retry.backoff_seconds", "number")}

        <hr className="border-slate-700" />
        <button onClick={onDelete} className="w-full py-1.5 bg-red-600/20 text-red-400 border border-red-600/30 rounded text-xs hover:bg-red-600/30">
          Delete Step
        </button>
      </div>
    </div>
  );
}
