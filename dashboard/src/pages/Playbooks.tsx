import { Plus } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import api from "../lib/api";

interface Playbook {
  id: string;
  name: string;
  version: number;
  enabled: boolean;
  trigger_type: string;
  created_at: string;
  updated_at: string;
}

interface PaginatedResponse {
  items: Playbook[];
  total: number;
  page: number;
  limit: number;
}

export default function Playbooks() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();

  const page = parseInt(params.get("page") || "1");
  const search = params.get("search") || "";
  const enabledFilter = params.get("enabled");

  const queryParams: Record<string, any> = { page, limit: 20 };
  if (search) queryParams.search = search;
  if (enabledFilter !== null && enabledFilter !== "") queryParams.enabled = enabledFilter === "true";

  const { data, isLoading, refetch } = useApiGet<PaginatedResponse>(["playbooks"], "/playbooks", queryParams);

  const toggleEnabled = async (pb: Playbook, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.patch(`/playbooks/${pb.id}`, { enabled: !pb.enabled });
      refetch();
    } catch {
      // ignore
    }
  };

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
        <h1 className="text-2xl font-bold">Playbooks</h1>
        <button
          onClick={() => navigate("/playbooks/new")}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-md text-sm font-medium transition-colors"
        >
          <Plus size={16} /> New Playbook
        </button>
      </div>

      <div className="flex flex-wrap gap-3 mb-4">
        <input
          type="text"
          placeholder="Search..."
          value={search}
          onChange={(e) => updateFilter("search", e.target.value)}
          className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={enabledFilter ?? ""}
          onChange={(e) => updateFilter("enabled", e.target.value)}
          className="px-3 py-1.5 bg-slate-800 border border-slate-600 rounded text-sm text-white"
        >
          <option value="">All</option>
          <option value="true">Enabled</option>
          <option value="false">Disabled</option>
        </select>
      </div>

      <div className="bg-slate-800/50 rounded-lg border border-slate-700 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-400">
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">Version</th>
              <th className="px-4 py-3 font-medium">Trigger</th>
              <th className="px-4 py-3 font-medium">Enabled</th>
              <th className="px-4 py-3 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">Loading...</td></tr>
            ) : !data?.items.length ? (
              <tr><td colSpan={5} className="px-4 py-8 text-center text-slate-400">No playbooks found</td></tr>
            ) : (
              data.items.map((pb) => (
                <tr
                  key={pb.id}
                  onClick={() => navigate(`/playbooks/${pb.id}`)}
                  className="border-b border-slate-700/50 hover:bg-slate-700/30 cursor-pointer transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-white">{pb.name}</td>
                  <td className="px-4 py-3 text-slate-300">v{pb.version}</td>
                  <td className="px-4 py-3"><Badge value={pb.trigger_type} /></td>
                  <td className="px-4 py-3">
                    <button
                      onClick={(e) => toggleEnabled(pb, e)}
                      className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${pb.enabled ? "bg-green-600" : "bg-slate-600"}`}
                    >
                      <span className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${pb.enabled ? "translate-x-4.5" : "translate-x-0.5"}`} />
                    </button>
                  </td>
                  <td className="px-4 py-3 text-slate-400">{new Date(pb.updated_at).toLocaleDateString()}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {data && data.total > 20 && (
        <div className="flex justify-center gap-2 mt-4">
          <button onClick={() => updateFilter("page", String(page - 1))} disabled={page <= 1} className="px-3 py-1 bg-slate-800 border border-slate-600 rounded text-sm disabled:opacity-50">Previous</button>
          <span className="px-3 py-1 text-sm text-slate-400">Page {page} of {Math.ceil(data.total / 20)}</span>
          <button onClick={() => updateFilter("page", String(page + 1))} disabled={page * 20 >= data.total} className="px-3 py-1 bg-slate-800 border border-slate-600 rounded text-sm disabled:opacity-50">Next</button>
        </div>
      )}
    </div>
  );
}
