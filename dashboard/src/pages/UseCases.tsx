import { useNavigate, useSearchParams } from "react-router-dom";
import { useApiGet } from "../hooks/useApiQuery";
import Badge from "../components/ui/Badge";
import { Plus } from "lucide-react";

interface UseCase {
  id: string;
  name: string;
  status: string;
  severity: string;
  owner_id: string;
  mitre_techniques: string[];
  version: number;
  updated_at: string;
}

interface PaginatedResponse {
  items: UseCase[];
  total: number;
  page: number;
  limit: number;
}

const STATUSES = ["", "draft", "testing", "production", "deprecated"];
const SEVERITIES = ["", "critical", "high", "medium", "low", "informational"];

export default function UseCases() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const page = parseInt(params.get("page") || "1");
  const status = params.get("status") || "";
  const severity = params.get("severity") || "";
  const search = params.get("search") || "";

  const queryParams: Record<string, any> = { page, limit: 20 };
  if (status) queryParams.status = status;
  if (severity) queryParams.severity = severity;
  if (search) queryParams.search = search;

  const { data, isLoading } = useApiGet<PaginatedResponse>(["use-cases"], "/use-cases", queryParams);

  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    next.set("page", "1");
    setParams(next);
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Use Cases</h1>
        <button
          onClick={() => navigate("/use-cases/new")}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium text-white transition-colors"
        >
          <Plus size={16} /> New Use Case
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => updateFilter("search", e.target.value)}
          className="px-3 py-1.5 bg-inset border border-edge2 rounded text-sm text-fg placeholder-fg3 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={status}
          onChange={(e) => updateFilter("status", e.target.value)}
          className="px-3 py-1.5 bg-inset border border-edge2 rounded text-sm text-fg"
        >
          <option value="">All Statuses</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
        <select
          value={severity}
          onChange={(e) => updateFilter("severity", e.target.value)}
          className="px-3 py-1.5 bg-inset border border-edge2 rounded text-sm text-fg"
        >
          <option value="">All Severities</option>
          {SEVERITIES.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>
      </div>

      {/* Table */}
      <div className="bg-card-a rounded-lg border border-edge overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-edge text-left text-fg3">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Severity</th>
              <th className="px-4 py-3 font-medium">MITRE</th>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-fg3">Loading...</td></tr>
            ) : !data?.items.length ? (
              <tr><td colSpan={6} className="px-4 py-8 text-center text-fg3">No use cases found</td></tr>
            ) : (
              data.items.map((uc) => (
                <tr
                  key={uc.id}
                  onClick={() => navigate(`/use-cases/${uc.id}`)}
                  className="border-b border-edge-a hover:bg-hover-row cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-fg">{uc.name}</td>
                  <td className="px-4 py-3"><Badge value={uc.status} /></td>
                  <td className="px-4 py-3"><Badge value={uc.severity} /></td>
                  <td className="px-4 py-3 text-fg2">
                    {uc.mitre_techniques?.slice(0, 3).join(", ")}
                    {(uc.mitre_techniques?.length || 0) > 3 && "..."}
                  </td>
                  <td className="px-4 py-3 text-fg2">v{uc.version}</td>
                  <td className="px-4 py-3 text-fg3">{new Date(uc.updated_at).toLocaleDateString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {data && data.total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button
            onClick={() => updateFilter("page", String(page - 1))}
            disabled={page <= 1}
            className="px-3 py-1 bg-card border border-edge2 rounded text-sm disabled:opacity-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm text-fg3">
            Page {page} of {Math.ceil(data.total / 20)}
          </span>
          <button
            onClick={() => updateFilter("page", String(page + 1))}
            disabled={page * 20 >= data.total}
            className="px-3 py-1 bg-card border border-edge2 rounded text-sm disabled:opacity-50"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
