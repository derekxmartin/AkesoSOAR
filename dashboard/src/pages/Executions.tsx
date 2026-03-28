import { useNavigate, useSearchParams } from "react-router-dom";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import usePageTitle from "../hooks/usePageTitle";

interface Execution {
  id: string;
  playbook_id: string;
  playbook_version: number;
  trigger_alert_id: string | null;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_ms: number | null;
  created_at: string;
}

export default function Executions() {
  usePageTitle("Executions");
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const page = parseInt(params.get("page") || "1");
  const statusFilter = params.get("status") || "";

  const queryParams: Record<string, any> = { page, limit: 20 };
  if (statusFilter) queryParams.status = statusFilter;

  const { data, isLoading } = useApiGet<any>(["executions"], "/executions", queryParams);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Executions</h1>

      <div className="flex gap-3 mb-4">
        <select
          value={statusFilter}
          onChange={(e) => {
            const next = new URLSearchParams(params);
            if (e.target.value) next.set("status", e.target.value);
            else next.delete("status");
            next.set("page", "1");
            setParams(next);
          }}
          className="px-3 py-1.5 bg-inset border border-edge2 rounded text-sm text-fg"
        >
          <option value="">All Statuses</option>
          {["queued", "running", "paused", "completed", "failed", "cancelled"].map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      <div className="bg-card-a rounded-lg border border-edge overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-edge text-left text-fg3">
              <th className="px-4 py-3 font-medium">ID</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Alert</th>
              <th className="px-4 py-3 font-medium">Duration</th>
              <th className="px-4 py-3 font-medium">Started</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-fg3">Loading...</td></tr>
            ) : !data?.items.length ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-fg3">No executions found</td></tr>
            ) : (
              data.items.map((ex: Execution) => (
                <tr
                  key={ex.id}
                  onClick={() => navigate(`/executions/${ex.id}`)}
                  className="border-b border-edge-a hover:bg-hover-row cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-mono text-xs text-fg2">{ex.id.slice(0, 12)}...</td>
                  <td className="px-4 py-3"><Badge value={ex.status} /></td>
                  <td className="px-4 py-3 text-fg2">{ex.trigger_alert_id || "manual"}</td>
                  <td className="px-4 py-3 text-fg2">{ex.duration_ms != null ? `${ex.duration_ms}ms` : "—"}</td>
                  <td className="px-4 py-3 text-fg3">{ex.started_at ? new Date(ex.started_at).toLocaleString() : "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
