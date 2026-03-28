import { Handle, Position, type NodeProps } from "@xyflow/react";
import { cn } from "../../lib/utils";

export interface StepNodeData {
  label: string;
  stepType: "action" | "condition" | "human_task" | "transform" | "parallel";
  connector?: string;
  operation?: string;
  status?: string; // For execution visualization
  [key: string]: any;
}

const TYPE_STYLES: Record<string, { bg: string; border: string; shape?: string }> = {
  action: { bg: "bg-blue-900/60", border: "border-blue-500" },
  condition: { bg: "bg-yellow-900/60", border: "border-yellow-500", shape: "rotate-45" },
  human_task: { bg: "bg-orange-900/60", border: "border-orange-500" },
  transform: { bg: "bg-slate-700/60", border: "border-slate-500" },
  parallel: { bg: "bg-purple-900/60", border: "border-purple-500" },
};

const STATUS_RING: Record<string, string> = {
  pending: "ring-slate-500",
  running: "ring-blue-400 animate-pulse",
  success: "ring-green-400",
  failed: "ring-red-400",
  skipped: "ring-slate-500",
  waiting: "ring-orange-400 animate-pulse",
};

const TYPE_ICONS: Record<string, string> = {
  action: "\u26A1",
  condition: "\u2753",
  human_task: "\u270B",
  transform: "\u{1F504}",
  parallel: "\u2261",
};

export default function StepNode({ data, selected }: NodeProps) {
  const d = data as StepNodeData;
  const style = TYPE_STYLES[d.stepType] || TYPE_STYLES.action;
  const statusRing = d.status ? STATUS_RING[d.status] || "" : "";

  const isCondition = d.stepType === "condition";

  return (
    <div
      className={cn(
        "px-4 py-3 border-2 shadow-lg min-w-[160px] text-center",
        style.bg,
        style.border,
        selected && "ring-2 ring-white",
        statusRing && `ring-2 ${statusRing}`,
        isCondition ? "rounded-lg" : "rounded-lg"
      )}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-400 !w-2 !h-2" />

      <div className="text-xs text-fg3 mb-1">
        {TYPE_ICONS[d.stepType]} {d.stepType}
      </div>
      <div className="text-sm font-medium text-fg">{d.label}</div>
      {d.connector && (
        <div className="text-xs text-fg3 mt-1">
          {d.connector}.{d.operation}
        </div>
      )}

      {isCondition ? (
        <>
          <Handle type="source" position={Position.Bottom} id="true" style={{ left: "30%" }} className="!bg-green-400 !w-2 !h-2" />
          <Handle type="source" position={Position.Bottom} id="false" style={{ left: "70%" }} className="!bg-red-400 !w-2 !h-2" />
        </>
      ) : (
        <Handle type="source" position={Position.Bottom} className="!bg-slate-400 !w-2 !h-2" />
      )}
    </div>
  );
}
