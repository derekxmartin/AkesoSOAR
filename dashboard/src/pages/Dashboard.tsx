import { Activity, AlertTriangle, CheckCircle, Clock, Hand, Shield } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import usePageTitle from "../hooks/usePageTitle";
import { useTheme } from "../context/ThemeContext";

interface OverviewMetrics {
  active_executions: number;
  total_executions: number;
  pending_human_tasks: number;
  mttr_seconds: number;
  coverage_percent: number;
  total_use_cases: number;
  production_use_cases: number;
  overdue_reviews: number;
  total_alerts: number;
}

interface PlaybookMetrics {
  period_days: number;
  total_executions: number;
  successes: number;
  failures: number;
  success_rate: number;
  avg_duration_ms: number;
  daily_trend: { date: string; total: number; completed: number; failed: number }[];
}

interface AlertSeverity {
  severity: string;
  count: number;
}

function StatCard({ icon: Icon, label, value, sub, color }: { icon: any; label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-card-a rounded-lg border border-edge p-5 flex items-start gap-4">
      <div className={`p-2 rounded-lg ${color || "bg-blue-500/10 text-blue-400"}`}>
        <Icon size={20} />
      </div>
      <div>
        <p className="text-xs font-medium text-fg3 uppercase tracking-wider">{label}</p>
        <p className="text-2xl font-bold text-fg mt-0.5">{value}</p>
        {sub && <p className="text-xs text-fg4 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

export default function Dashboard() {
  usePageTitle("Dashboard");
  const { theme } = useTheme();

  const { data: overview } = useApiGet<OverviewMetrics>(["metrics-overview"], "/metrics/overview", {}, { refetchInterval: 30000 });
  const { data: pbMetrics } = useApiGet<PlaybookMetrics>(["metrics-playbooks"], "/metrics/playbooks", { days: 30 }, { refetchInterval: 30000 });
  const { data: alertSev } = useApiGet<AlertSeverity[]>(["metrics-alerts-sev"], "/metrics/alerts-by-severity", {}, { refetchInterval: 30000 });
  const { data: execData } = useApiGet<any>(["executions-dash"], "/executions", { limit: 5 });
  const { data: htData } = useApiGet<any>(["human-tasks-dash"], "/human-tasks", { pending_only: true });

  const gridColor = theme === "dark" ? "#334155" : "#e2e8f0";
  const textColor = theme === "dark" ? "#94a3b8" : "#64748b";

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">SOC Overview</h1>

      {/* Stat cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard icon={AlertTriangle} label="Alerts" value={overview?.total_alerts ?? "—"} color="bg-red-500/10 text-red-400" />
        <StatCard icon={Activity} label="Active Runs" value={overview?.active_executions ?? "—"} color="bg-blue-500/10 text-blue-400" />
        <StatCard icon={Hand} label="Pending Tasks" value={overview?.pending_human_tasks ?? "—"} color="bg-yellow-500/10 text-yellow-400" />
        <StatCard icon={Clock} label="MTTR" value={overview ? `${overview.mttr_seconds}s` : "—"} color="bg-purple-500/10 text-purple-400" />
        <StatCard icon={Shield} label="Coverage" value={overview ? `${overview.coverage_percent}%` : "—"} sub={overview ? `${overview.production_use_cases}/${overview.total_use_cases} UC` : ""} color="bg-green-500/10 text-green-400" />
        <StatCard icon={CheckCircle} label="Success Rate" value={pbMetrics ? `${pbMetrics.success_rate}%` : "—"} sub={pbMetrics ? `${pbMetrics.successes}/${pbMetrics.total_executions}` : ""} color="bg-emerald-500/10 text-emerald-400" />
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Execution trend */}
        <div className="bg-card-a rounded-lg border border-edge p-5">
          <h2 className="text-sm font-semibold mb-4">Execution Trend (30 days)</h2>
          {pbMetrics?.daily_trend?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={pbMetrics.daily_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: textColor }} tickFormatter={(v) => v.slice(5)} />
                <YAxis tick={{ fontSize: 10, fill: textColor }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: theme === "dark" ? "#1e293b" : "#fff", border: "none", borderRadius: 8, fontSize: 12 }} />
                <Line type="monotone" dataKey="completed" stroke="#22c55e" strokeWidth={2} dot={false} name="Completed" />
                <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} dot={false} name="Failed" />
                <Line type="monotone" dataKey="total" stroke="#3b82f6" strokeWidth={1} strokeDasharray="4 4" dot={false} name="Total" />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-fg3 text-sm">No execution data yet</div>
          )}
        </div>

        {/* Alerts by severity */}
        <div className="bg-card-a rounded-lg border border-edge p-5">
          <h2 className="text-sm font-semibold mb-4">Alerts by Severity</h2>
          {alertSev?.length ? (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={alertSev}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="severity" tick={{ fontSize: 10, fill: textColor }} />
                <YAxis tick={{ fontSize: 10, fill: textColor }} allowDecimals={false} />
                <Tooltip contentStyle={{ backgroundColor: theme === "dark" ? "#1e293b" : "#fff", border: "none", borderRadius: 8, fontSize: 12 }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} fill="#3b82f6">
                  {alertSev.map((entry, i) => {
                    const colors: Record<string, string> = { critical: "#ef4444", high: "#f97316", medium: "#eab308", low: "#3b82f6", informational: "#64748b" };
                    return <rect key={i} fill={colors[entry.severity] || "#3b82f6"} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[220px] flex items-center justify-center text-fg3 text-sm">No alert data yet</div>
          )}
        </div>
      </div>

      {/* Tables row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent executions */}
        <div className="bg-card-a rounded-lg border border-edge p-5">
          <h2 className="text-sm font-semibold mb-3">Recent Executions</h2>
          {execData?.items?.length ? (
            <div className="space-y-2">
              {execData.items.map((e: any) => (
                <div key={e.id} className="flex items-center justify-between text-sm">
                  <span className="text-fg2 font-mono text-xs">{e.id.slice(0, 8)}</span>
                  <Badge value={e.status} />
                  <span className="text-fg3">{e.duration_ms != null ? `${e.duration_ms}ms` : "—"}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-fg3 text-sm">No executions yet</p>
          )}
        </div>

        {/* Pending human tasks */}
        <div className="bg-card-a rounded-lg border border-edge p-5">
          <h2 className="text-sm font-semibold mb-3">Pending Approvals</h2>
          {htData?.items?.length ? (
            <div className="space-y-2">
              {htData.items.map((t: any) => (
                <div key={t.id} className="flex items-center justify-between text-sm p-2 bg-chip-a rounded">
                  <div>
                    <span className="text-fg font-medium">{t.step_id}</span>
                    <span className="text-fg3 ml-2 text-xs">{t.prompt.slice(0, 50)}</span>
                  </div>
                  <Badge value={t.assignee_role} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-fg3 text-sm">No pending tasks</p>
          )}
        </div>
      </div>
    </div>
  );
}
