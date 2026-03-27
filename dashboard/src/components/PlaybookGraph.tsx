import {
  Background,
  Controls,
  type Edge,
  MiniMap,
  type Node,
  ReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCallback, useMemo } from "react";
import StepNode, { type StepNodeData } from "./nodes/StepNode";

const nodeTypes = { step: StepNode };

interface PlaybookStep {
  id: string;
  name: string;
  type: string;
  action?: { connector: string; operation: string; params?: Record<string, any> };
  condition?: { expression: string; branches: Record<string, string> };
  human_task?: { prompt: string; assignee_role: string };
  transform?: { expression: string };
  parallel?: { branches: { steps: string[] }[]; join: string };
  on_success?: string;
  on_failure?: string;
  timeout_seconds?: number;
  retry?: { max_attempts: number; backoff_seconds: number };
}

interface Props {
  steps: PlaybookStep[];
  stepStatuses?: Record<string, string>; // step_id → status (for execution view)
  onNodeClick?: (stepId: string, step: PlaybookStep) => void;
  interactive?: boolean;
}

function buildGraph(
  steps: PlaybookStep[],
  stepStatuses?: Record<string, string>
): { nodes: Node[]; edges: Edge[] } {
  const nodes: Node[] = [];
  const edges: Edge[] = [];
  const Y_SPACING = 120;
  const X_SPACING = 250;

  // Position nodes in a simple top-down layout
  // Group: first lay out the main chain, then position parallel/branch targets
  const positioned = new Set<string>();
  let y = 0;

  // Follow the main chain from the first step
  const stepMap = new Map(steps.map((s) => [s.id, s]));
  const mainChain: string[] = [];
  let current: string | undefined = steps[0]?.id;

  while (current && !mainChain.includes(current)) {
    mainChain.push(current);
    const s = stepMap.get(current);
    if (!s) break;
    current = s.on_success || undefined;
    // For conditions, follow the "true" branch as main chain
    if (s.type === "condition" && s.condition?.branches) {
      current = s.condition.branches["true"] || s.condition.branches["false"];
    }
  }

  // Position main chain
  for (const id of mainChain) {
    const s = stepMap.get(id)!;
    nodes.push({
      id,
      type: "step",
      position: { x: 300, y },
      data: {
        label: s.name,
        stepType: s.type as StepNodeData["stepType"],
        connector: s.action?.connector,
        operation: s.action?.operation,
        status: stepStatuses?.[id],
      },
    });
    positioned.add(id);
    y += Y_SPACING;
  }

  // Position remaining steps (branch targets, parallel sub-steps)
  let xOffset = 0;
  for (const s of steps) {
    if (positioned.has(s.id)) continue;
    xOffset += X_SPACING;
    nodes.push({
      id: s.id,
      type: "step",
      position: { x: 300 + xOffset, y: Y_SPACING * 2 },
      data: {
        label: s.name,
        stepType: s.type as StepNodeData["stepType"],
        connector: s.action?.connector,
        operation: s.action?.operation,
        status: stepStatuses?.[s.id],
      },
    });
    positioned.add(s.id);
  }

  // Build edges
  for (const s of steps) {
    if (s.on_success && stepMap.has(s.on_success) && s.type !== "condition") {
      edges.push({
        id: `${s.id}->${s.on_success}`,
        source: s.id,
        target: s.on_success,
        animated: false,
        style: { stroke: "#64748b" },
      });
    }

    if (s.on_failure && s.on_failure !== "abort" && stepMap.has(s.on_failure)) {
      edges.push({
        id: `${s.id}->fail->${s.on_failure}`,
        source: s.id,
        target: s.on_failure,
        animated: false,
        label: "fail",
        style: { stroke: "#ef4444" },
        labelStyle: { fill: "#ef4444", fontSize: 10 },
      });
    }

    if (s.type === "condition" && s.condition?.branches) {
      const { branches } = s.condition;
      if (branches["true"] && stepMap.has(branches["true"])) {
        edges.push({
          id: `${s.id}->true->${branches["true"]}`,
          source: s.id,
          sourceHandle: "true",
          target: branches["true"],
          label: "true",
          style: { stroke: "#22c55e" },
          labelStyle: { fill: "#22c55e", fontSize: 10 },
        });
      }
      if (branches["false"] && stepMap.has(branches["false"])) {
        edges.push({
          id: `${s.id}->false->${branches["false"]}`,
          source: s.id,
          sourceHandle: "false",
          target: branches["false"],
          label: "false",
          style: { stroke: "#ef4444" },
          labelStyle: { fill: "#ef4444", fontSize: 10 },
        });
      }
    }

    // Parallel branch edges
    if (s.type === "parallel" && s.parallel?.branches) {
      for (const branch of s.parallel.branches) {
        if (branch.steps.length > 0 && stepMap.has(branch.steps[0])) {
          edges.push({
            id: `${s.id}->par->${branch.steps[0]}`,
            source: s.id,
            target: branch.steps[0],
            animated: true,
            style: { stroke: "#a855f7" },
          });
        }
      }
    }
  }

  return { nodes, edges };
}

export default function PlaybookGraph({ steps, stepStatuses, onNodeClick, interactive = false }: Props) {
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => buildGraph(steps, stepStatuses),
    [steps, stepStatuses]
  );

  const handleNodeClick = useCallback(
    (_: any, node: Node) => {
      const step = steps.find((s) => s.id === node.id);
      if (step && onNodeClick) onNodeClick(node.id, step);
    },
    [steps, onNodeClick]
  );

  return (
    <ReactFlowProvider>
      <div className="h-[500px] bg-slate-900 rounded-lg border border-slate-700">
        <ReactFlow
          nodes={initialNodes}
          edges={initialEdges}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          fitView
          nodesDraggable={interactive}
          nodesConnectable={interactive}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#334155" gap={20} />
          <Controls className="!bg-slate-800 !border-slate-600 [&>button]:!bg-slate-700 [&>button]:!border-slate-600 [&>button]:!text-white" />
          <MiniMap
            className="!bg-slate-800 !border-slate-600"
            nodeColor={() => "#3b82f6"}
            maskColor="rgba(0,0,0,0.5)"
          />
        </ReactFlow>
      </div>
    </ReactFlowProvider>
  );
}
