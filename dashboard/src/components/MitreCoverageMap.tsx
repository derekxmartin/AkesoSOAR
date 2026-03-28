import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useApiGet } from "../hooks/useApiQuery";

interface TechniqueData {
  id: string;
  name: string;
  count: number;
  coverage: "none" | "partial" | "full";
  use_cases: { id: string; name: string; status: string }[];
}

interface TacticData {
  id: string;
  name: string;
  techniques: TechniqueData[];
}

interface CoverageMatrix {
  summary: { total_techniques: number; covered: number; partial: number; gaps: number };
  matrix: Record<string, TacticData>;
}

const COVERAGE_COLORS = {
  full: "bg-green-600 hover:bg-green-500",
  partial: "bg-yellow-600 hover:bg-yellow-500",
  none: "bg-red-900/40 hover:bg-red-900/60",
};

export default function MitreCoverageMap() {
  const navigate = useNavigate();
  const { data, isLoading } = useApiGet<CoverageMatrix>(["mitre-coverage"], "/coverage/mitre");
  const [selectedTech, setSelectedTech] = useState<TechniqueData | null>(null);
  const [tooltipTech, setTooltipTech] = useState<{ tech: TechniqueData; x: number; y: number } | null>(null);

  if (isLoading) return <div className="text-fg3">Loading coverage data...</div>;
  if (!data?.matrix) return <div className="text-fg3">No coverage data</div>;

  const allTactics = Object.values(data.matrix);

  return (
    <div className="space-y-4">
      {/* Summary bar */}
      <div className="flex items-center gap-6 text-sm">
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded bg-green-600" />
          <span className="text-fg2">Production ({data.summary.covered})</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded bg-yellow-600" />
          <span className="text-fg2">Draft/Testing ({data.summary.partial})</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded bg-red-900/50" />
          <span className="text-fg2">Gap ({data.summary.gaps})</span>
        </div>
        <span className="text-fg4 ml-auto">
          {data.summary.covered + data.summary.partial}/{data.summary.total_techniques} techniques covered
        </span>
      </div>

      {/* Heatmap grid */}
      <div className="overflow-x-auto">
        <div className="flex gap-2 min-w-max">
          {allTactics.map((tactic) => (
            <div key={tactic.id} className="flex flex-col gap-1 min-w-[110px]">
              {/* Tactic header */}
              <div className="text-[10px] font-semibold text-fg3 uppercase tracking-wide px-1 py-1.5 border-b border-edge mb-1 text-center">
                {tactic.name}
              </div>
              {/* Technique cells */}
              {tactic.techniques.map((tech) => (
                <button
                  key={tech.id}
                  onClick={() => setSelectedTech(selectedTech?.id === tech.id ? null : tech)}
                  onMouseEnter={(e) => {
                    const rect = e.currentTarget.getBoundingClientRect();
                    setTooltipTech({ tech, x: rect.right + 8, y: rect.top });
                  }}
                  onMouseLeave={() => setTooltipTech(null)}
                  className={`px-2 py-1.5 rounded text-[10px] text-white/90 text-left transition-colors ${
                    COVERAGE_COLORS[tech.coverage]
                  } ${selectedTech?.id === tech.id ? "ring-2 ring-blue-400" : ""}`}
                >
                  <div className="font-mono">{tech.id}</div>
                </button>
              ))}
            </div>
          ))}
        </div>
      </div>

      {/* Tooltip */}
      {tooltipTech && (
        <div
          style={{
            position: "fixed",
            left: Math.min(tooltipTech.x, window.innerWidth - 260),
            top: tooltipTech.y,
            zIndex: 50,
          }}
          className="bg-app border border-edge rounded-lg shadow-xl p-3 text-xs w-56 pointer-events-none"
        >
          <div className="font-mono text-fg font-bold">{tooltipTech.tech.id}</div>
          <div className="text-fg2 mt-0.5">{tooltipTech.tech.name}</div>
          <div className="text-fg4 mt-1">
            {tooltipTech.tech.count} use case{tooltipTech.tech.count !== 1 ? "s" : ""}
            {" · "}
            <span className={tooltipTech.tech.coverage === "full" ? "text-green-400" : tooltipTech.tech.coverage === "partial" ? "text-yellow-400" : "text-red-400"}>
              {tooltipTech.tech.coverage}
            </span>
          </div>
        </div>
      )}

      {/* Selected technique detail */}
      {selectedTech && (
        <div className="bg-card-a rounded-lg border border-edge p-4">
          <div className="flex items-center justify-between mb-3">
            <div>
              <span className="font-mono text-sm font-bold text-fg">{selectedTech.id}</span>
              <span className="text-fg2 ml-2">{selectedTech.name}</span>
            </div>
            <button onClick={() => setSelectedTech(null)} className="text-fg3 hover:text-fg text-xs">
              Close
            </button>
          </div>
          {selectedTech.use_cases.length > 0 ? (
            <div className="space-y-1.5">
              {selectedTech.use_cases.map((uc) => (
                <button
                  key={uc.id}
                  onClick={() => navigate(`/use-cases/${uc.id}`)}
                  className="flex items-center justify-between w-full text-left p-2 rounded hover:bg-hover text-sm"
                >
                  <span className="text-fg">{uc.name}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${
                    uc.status === "production" ? "bg-green-600/20 text-green-400" :
                    uc.status === "testing" ? "bg-yellow-600/20 text-yellow-400" :
                    "bg-slate-600/20 text-fg3"
                  }`}>
                    {uc.status}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-fg4 text-sm">No use cases cover this technique</p>
          )}
        </div>
      )}
    </div>
  );
}
