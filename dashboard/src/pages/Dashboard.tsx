import { useApiGet } from "../hooks/useApiQuery";
import Badge from "../components/ui/Badge";

export default function Dashboard() {
  const { data: ucData } = useApiGet<any>(["use-cases-dash"], "/use-cases", { limit: 5 });
  const { data: execData } = useApiGet<any>(["executions-dash"], "/executions", { limit: 5 });
  const { data: alertData } = useApiGet<any>(["alerts-dash"], "/alerts", { limit: 5 });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-card-a rounded-lg border border-edge p-6">
          <h3 className="text-sm font-medium text-fg3 mb-1">Use Cases</h3>
          <p className="text-3xl font-bold text-fg">{ucData?.total ?? "—"}</p>
        </div>
        <div className="bg-card-a rounded-lg border border-edge p-6">
          <h3 className="text-sm font-medium text-fg3 mb-1">Executions</h3>
          <p className="text-3xl font-bold text-fg">{execData?.total ?? "—"}</p>
        </div>
        <div className="bg-card-a rounded-lg border border-edge p-6">
          <h3 className="text-sm font-medium text-fg3 mb-1">Alerts Ingested</h3>
          <p className="text-3xl font-bold text-fg">{alertData?.total ?? "—"}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-card-a rounded-lg border border-edge p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Executions</h2>
          {execData?.items?.length ? (
            <div className="space-y-2">
              {execData.items.map((e: any) => (
                <div key={e.id} className="flex items-center justify-between text-sm">
                  <span className="text-fg2 font-mono text-xs">{e.id.slice(0, 8)}...</span>
                  <Badge value={e.status} />
                  <span className="text-fg3">{e.duration_ms}ms</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-fg3 text-sm">No executions yet</p>
          )}
        </div>

        <div className="bg-card-a rounded-lg border border-edge p-6">
          <h2 className="text-lg font-semibold mb-4">Recent Alerts</h2>
          {alertData?.items?.length ? (
            <div className="space-y-2">
              {alertData.items.map((a: any) => (
                <div key={a.id} className="flex items-center justify-between text-sm">
                  <span className="text-fg">{a.title}</span>
                  <Badge value={a.severity} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-fg3 text-sm">No alerts yet</p>
          )}
        </div>
      </div>
    </div>
  );
}
