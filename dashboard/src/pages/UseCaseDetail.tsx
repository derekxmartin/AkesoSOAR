import DOMPurify from "dompurify";
import { ArrowLeft, Edit } from "lucide-react";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import usePageTitle from "../hooks/usePageTitle";
import { cn } from "../lib/utils";

interface UseCase {
  id: string;
  name: string;
  description: string;
  version: number;
  status: string;
  severity: string;
  owner_id: string;
  mitre_tactics: string[];
  mitre_techniques: string[];
  sigma_rule_ids: string[];
  siem_alert_query: string | null;
  severity_threshold: string | null;
  escalation_policy: string;
  notification_channels: string[];
  summary: string;
  investigation_guide: string;
  false_positive_guidance: string;
  references: string[];
  review_cadence_days: number;
  last_reviewed_at: string | null;
  next_review_at: string | null;
  created_at: string;
  updated_at: string;
}

interface Version {
  id: string;
  version: number;
  change_description: string;
  changed_by: string;
  created_at: string;
}

interface AuditEntry {
  id: string;
  event_type: string;
  description: string;
  actor: string;
  created_at: string;
}

const TABS = ["Overview", "Detection", "Response", "Documentation", "Versions", "Audit Log"];

function Markdown({ content }: { content: string }) {
  const html = content
    .replace(/^### (.+)$/gm, "<h3 class='text-lg font-semibold mt-4 mb-2'>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2 class='text-xl font-semibold mt-4 mb-2'>$1</h2>")
    .replace(/^# (.+)$/gm, "<h1 class='text-2xl font-bold mt-4 mb-2'>$1</h1>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/^- (.+)$/gm, "<li class='ml-4'>$1</li>")
    .replace(/\n/g, "<br/>");
  return (
    <div
      className="prose max-w-none text-sm text-fg2"
      dangerouslySetInnerHTML={{ __html: DOMPurify.sanitize(html) }}
    />
  );
}

export default function UseCaseDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState("Overview");

  const { data: uc, isLoading } = useApiGet<UseCase>(["use-case", id!], `/use-cases/${id}`);
  const { data: versions } = useApiGet<Version[]>(["use-case-versions", id!], `/use-cases/${id}/versions`);
  const { data: auditData } = useApiGet<{ items: AuditEntry[]; total: number }>(
    ["audit", "use_case", id!],
    "/audit-log",
    { resource_type: "use_case", resource_id: id }
  );
  const { data: playbooks } = useApiGet<any[]>(["uc-playbooks", id!], `/use-cases/${id}/playbooks`);

  usePageTitle(uc?.name ? `${uc.name} — Use Case` : "Use Case");

  if (isLoading || !uc) return <div className="text-fg3">Loading...</div>;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate("/use-cases")} className="text-fg3 hover:text-fg">
          <ArrowLeft size={20} />
        </button>
        <div className="flex-1">
          <h1 className="text-2xl font-bold">{uc.name}</h1>
          <p className="text-fg3 text-sm mt-1">{uc.description}</p>
        </div>
        <Badge value={uc.status} />
        <Badge value={uc.severity} />
        <span className="text-sm text-fg3">v{uc.version}</span>
        <button
          onClick={() => navigate(`/use-cases/${id}/edit`)}
          className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded text-sm text-white"
        >
          <Edit size={14} /> Edit
        </button>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-edge mb-6">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              activeTab === tab
                ? "border-blue-500 text-blue-400"
                : "border-transparent text-fg3 hover:text-fg"
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-card-a rounded-lg border border-edge p-6">
        {activeTab === "Overview" && (
          <div className="grid grid-cols-2 gap-6 text-sm">
            <div><span className="text-fg3">Owner:</span> <span className="text-fg ml-2">{uc.owner_id.slice(0, 8)}...</span></div>
            <div><span className="text-fg3">Review Cadence:</span> <span className="text-fg ml-2">{uc.review_cadence_days} days</span></div>
            <div><span className="text-fg3">Last Reviewed:</span> <span className="text-fg ml-2">{uc.last_reviewed_at ? new Date(uc.last_reviewed_at).toLocaleDateString() : "Never"}</span></div>
            <div><span className="text-fg3">Next Review:</span> <span className="text-fg ml-2">{uc.next_review_at ? new Date(uc.next_review_at).toLocaleDateString() : "N/A"}</span></div>
            <div><span className="text-fg3">Escalation:</span> <span className="text-fg ml-2">{uc.escalation_policy}</span></div>
            <div><span className="text-fg3">Created:</span> <span className="text-fg ml-2">{new Date(uc.created_at).toLocaleDateString()}</span></div>
            <div className="col-span-2">
              <span className="text-fg3">MITRE Tactics:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {uc.mitre_tactics.map((t) => <Badge key={t} value={t} />)}
              </div>
            </div>
            <div className="col-span-2">
              <span className="text-fg3">MITRE Techniques:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {uc.mitre_techniques.map((t) => <Badge key={t} value={t} />)}
              </div>
            </div>
            {uc.summary && (
              <div className="col-span-2">
                <span className="text-fg3">Summary:</span>
                <p className="text-fg mt-1">{uc.summary}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === "Detection" && (
          <div className="space-y-4 text-sm">
            <div>
              <h3 className="text-fg3 font-medium mb-2">Sigma Rule IDs</h3>
              <div className="flex flex-wrap gap-2">
                {uc.sigma_rule_ids.length ? uc.sigma_rule_ids.map((r) => (
                  <span key={r} className="px-2 py-1 bg-chip rounded text-fg2">{r}</span>
                )) : <span className="text-fg4">None configured</span>}
              </div>
            </div>
            {uc.siem_alert_query && (
              <div>
                <h3 className="text-fg3 font-medium mb-2">SIEM Alert Query</h3>
                <code className="block p-3 bg-chip rounded text-fg2">{uc.siem_alert_query}</code>
              </div>
            )}
            {uc.severity_threshold && (
              <div>
                <h3 className="text-fg3 font-medium mb-2">Severity Threshold</h3>
                <Badge value={uc.severity_threshold} />
              </div>
            )}
          </div>
        )}

        {activeTab === "Response" && (
          <div className="space-y-4 text-sm">
            <div>
              <h3 className="text-fg3 font-medium mb-2">Linked Playbooks</h3>
              {playbooks?.length ? (
                <div className="space-y-2">
                  {playbooks.map((pb: any) => (
                    <div
                      key={pb.id}
                      onClick={() => navigate(`/playbooks/${pb.id}`)}
                      className="flex items-center justify-between p-3 bg-chip-a rounded cursor-pointer hover:bg-hover"
                    >
                      <span className="text-fg">{pb.name}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-fg3">v{pb.version}</span>
                        <Badge value={pb.enabled ? "production" : "deprecated"} />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <span className="text-fg4">No playbooks linked</span>
              )}
            </div>
            <div>
              <h3 className="text-fg3 font-medium mb-2">Notification Channels</h3>
              {uc.notification_channels.length ? (
                <div className="flex flex-wrap gap-2">
                  {uc.notification_channels.map((c) => (
                    <span key={c} className="px-2 py-1 bg-chip rounded text-fg2">{c}</span>
                  ))}
                </div>
              ) : (
                <span className="text-fg4">None configured</span>
              )}
            </div>
          </div>
        )}

        {activeTab === "Documentation" && (
          <div className="space-y-6">
            {uc.investigation_guide && (
              <div>
                <h3 className="text-lg font-medium text-fg mb-2">Investigation Guide</h3>
                <Markdown content={uc.investigation_guide} />
              </div>
            )}
            {uc.false_positive_guidance && (
              <div>
                <h3 className="text-lg font-medium text-fg mb-2">False Positive Guidance</h3>
                <Markdown content={uc.false_positive_guidance} />
              </div>
            )}
            {uc.references.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-fg mb-2">References</h3>
                <ul className="list-disc list-inside text-sm text-blue-400">
                  {uc.references.map((r, i) => <li key={i}><a href={r} target="_blank" rel="noopener">{r}</a></li>)}
                </ul>
              </div>
            )}
          </div>
        )}

        {activeTab === "Versions" && (
          <div className="space-y-3">
            {versions?.map((v) => (
              <div key={v.id} className="flex items-center justify-between p-3 bg-chip-a rounded text-sm">
                <div>
                  <span className="font-medium text-fg">v{v.version}</span>
                  <span className="text-fg3 ml-3">{v.change_description}</span>
                </div>
                <span className="text-fg3">{new Date(v.created_at).toLocaleString()}</span>
              </div>
            ))}
            {!versions?.length && <p className="text-fg3">No version history</p>}
          </div>
        )}

        {activeTab === "Audit Log" && (
          <div className="space-y-2">
            {auditData?.items.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between p-3 bg-chip-a rounded text-sm">
                <div>
                  <Badge value={entry.event_type.split(".").pop() || entry.event_type} />
                  <span className="text-fg2 ml-3">{entry.description}</span>
                </div>
                <span className="text-fg3">{new Date(entry.created_at).toLocaleString()}</span>
              </div>
            ))}
            {!auditData?.items.length && <p className="text-fg3">No audit entries</p>}
          </div>
        )}
      </div>
    </div>
  );
}
