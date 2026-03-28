import { ArrowLeft, Save } from "lucide-react";
import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import MitrePicker from "../components/MitrePicker";
import Badge from "../components/ui/Badge";
import { useApiGet } from "../hooks/useApiQuery";
import usePageTitle from "../hooks/usePageTitle";
import api from "../lib/api";

const SEVERITIES = ["critical", "high", "medium", "low", "informational"];
const ESCALATION_POLICIES = ["auto", "manual", "conditional"];

export default function UseCaseEditor() {
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === "new";
  const navigate = useNavigate();

  usePageTitle(isNew ? "New Use Case" : `Edit Use Case`);

  const { data: existing } = useApiGet<any>(
    ["use-case", id!],
    `/use-cases/${id}`,
  );

  const [form, setForm] = useState({
    name: "",
    description: "",
    severity: "medium",
    mitre_tactics: [] as string[],
    mitre_techniques: [] as string[],
    sigma_rule_ids: "",
    siem_alert_query: "",
    severity_threshold: "",
    escalation_policy: "manual",
    notification_channels: "",
    summary: "",
    investigation_guide: "",
    false_positive_guidance: "",
    references: "",
    review_cadence_days: 90,
    change_description: "",
  });

  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [transitionTarget, setTransitionTarget] = useState("");
  const [transitionReason, setTransitionReason] = useState("");
  const [transitionError, setTransitionError] = useState("");

  useEffect(() => {
    if (!isNew && existing) {
      setForm({
        name: existing.name || "",
        description: existing.description || "",
        severity: existing.severity || "medium",
        mitre_tactics: existing.mitre_tactics || [],
        mitre_techniques: existing.mitre_techniques || [],
        sigma_rule_ids: (existing.sigma_rule_ids || []).join(", "),
        siem_alert_query: existing.siem_alert_query || "",
        severity_threshold: existing.severity_threshold || "",
        escalation_policy: existing.escalation_policy || "manual",
        notification_channels: (existing.notification_channels || []).join(", "),
        summary: existing.summary || "",
        investigation_guide: existing.investigation_guide || "",
        false_positive_guidance: existing.false_positive_guidance || "",
        references: (existing.references || []).join("\n"),
        review_cadence_days: existing.review_cadence_days || 90,
        change_description: "",
      });
    }
  }, [existing, isNew]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSaving(true);

    const body: any = {
      name: form.name,
      description: form.description,
      severity: form.severity,
      mitre_tactics: form.mitre_tactics,
      mitre_techniques: form.mitre_techniques,
      sigma_rule_ids: form.sigma_rule_ids.split(",").map((s) => s.trim()).filter(Boolean),
      siem_alert_query: form.siem_alert_query || null,
      severity_threshold: form.severity_threshold || null,
      escalation_policy: form.escalation_policy,
      notification_channels: form.notification_channels.split(",").map((s) => s.trim()).filter(Boolean),
      summary: form.summary,
      investigation_guide: form.investigation_guide,
      false_positive_guidance: form.false_positive_guidance,
      references: form.references.split("\n").map((s) => s.trim()).filter(Boolean),
      review_cadence_days: form.review_cadence_days,
    };

    try {
      if (isNew) {
        body.owner_id = JSON.parse(atob(localStorage.getItem("access_token")!.split(".")[1])).sub;
        const { data } = await api.post("/use-cases", body);
        navigate(`/use-cases/${data.id}`);
      } else {
        body.change_description = form.change_description;
        await api.patch(`/use-cases/${id}`, body);
        navigate(`/use-cases/${id}`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleTransition = async () => {
    if (!transitionTarget || !transitionReason) return;
    setTransitionError("");
    try {
      await api.post(`/use-cases/${id}/transition`, {
        to_status: transitionTarget,
        reason: transitionReason,
      });
      navigate(`/use-cases/${id}`);
    } catch (err: any) {
      setTransitionError(err.response?.data?.detail || "Transition failed");
    }
  };

  const field = (label: string, key: string, type: "text" | "textarea" | "number" | "select" = "text", options?: string[]) => (
    <div>
      <label className="block text-sm font-medium text-fg2 mb-1">{label}</label>
      {type === "textarea" ? (
        <textarea
          value={(form as any)[key]}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          rows={4}
          className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg placeholder-fg3 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      ) : type === "select" ? (
        <select
          value={(form as any)[key]}
          onChange={(e) => setForm({ ...form, [key]: e.target.value })}
          className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg"
        >
          {key === "severity_threshold" && <option value="">None</option>}
          {options?.map((o) => <option key={o} value={o}>{o.charAt(0).toUpperCase() + o.slice(1)}</option>)}
        </select>
      ) : (
        <input
          type={type}
          value={(form as any)[key]}
          onChange={(e) => setForm({ ...form, [key]: type === "number" ? parseInt(e.target.value) || 0 : e.target.value })}
          className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg placeholder-fg3 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      )}
    </div>
  );

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(isNew ? "/use-cases" : `/use-cases/${id}`)} className="text-fg3 hover:text-fg">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-2xl font-bold">{isNew ? "New Use Case" : `Edit: ${existing?.name || ""}`}</h1>
        {!isNew && existing && <Badge value={existing.status} />}
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">General</h2>
          {field("Name", "name")}
          {field("Description", "description", "textarea")}
          <div className="grid grid-cols-2 gap-4">
            {field("Severity", "severity", "select", SEVERITIES)}
            {field("Review Cadence (days)", "review_cadence_days", "number")}
          </div>
        </div>

        <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">MITRE ATT&CK Mapping</h2>
          <MitrePicker
            selectedTactics={form.mitre_tactics}
            selectedTechniques={form.mitre_techniques}
            onTacticsChange={(t) => setForm({ ...form, mitre_tactics: t })}
            onTechniquesChange={(t) => setForm({ ...form, mitre_techniques: t })}
          />
        </div>

        <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">Detection</h2>
          {field("Sigma Rule IDs (comma-separated)", "sigma_rule_ids")}
          {field("SIEM Alert Query", "siem_alert_query")}
          {field("Severity Threshold", "severity_threshold", "select", SEVERITIES)}
        </div>

        <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">Response</h2>
          {field("Escalation Policy", "escalation_policy", "select", ESCALATION_POLICIES)}
          {field("Notification Channels (comma-separated)", "notification_channels")}
        </div>

        <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">Documentation</h2>
          {field("Summary", "summary", "textarea")}
          {field("Investigation Guide (Markdown)", "investigation_guide", "textarea")}
          {field("False Positive Guidance", "false_positive_guidance", "textarea")}
          {field("References (one per line)", "references", "textarea")}
        </div>

        {!isNew && (
          <div className="bg-card-a rounded-lg border border-edge p-6 space-y-4">
            <h2 className="text-lg font-semibold text-fg">Change Description</h2>
            {field("What changed?", "change_description")}
          </div>
        )}

        {error && <p className="text-red-400 text-sm">{typeof error === "string" ? error : JSON.stringify(error)}</p>}

        <button
          type="submit"
          disabled={saving}
          className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 rounded-md font-medium text-white transition-colors"
        >
          <Save size={16} /> {saving ? "Saving..." : isNew ? "Create Use Case" : "Save Changes"}
        </button>
      </form>

      {!isNew && existing && (
        <div className="mt-8 bg-card-a rounded-lg border border-edge p-6 space-y-4">
          <h2 className="text-lg font-semibold text-fg">Lifecycle Transition</h2>
          <p className="text-sm text-fg3">Current status: <Badge value={existing.status} /></p>
          <div className="flex gap-3 items-end">
            <div className="flex-1">
              <label className="block text-sm text-fg2 mb-1">Transition To</label>
              <select
                value={transitionTarget}
                onChange={(e) => setTransitionTarget(e.target.value)}
                className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg"
              >
                <option value="">Select...</option>
                {existing.status === "draft" && <><option value="testing">Testing</option><option value="deprecated">Deprecated</option></>}
                {existing.status === "testing" && <option value="production">Production</option>}
                {existing.status === "production" && <><option value="testing">Testing (demote)</option><option value="deprecated">Deprecated</option></>}
              </select>
            </div>
            <div className="flex-1">
              <label className="block text-sm text-fg2 mb-1">Reason</label>
              <input
                type="text"
                value={transitionReason}
                onChange={(e) => setTransitionReason(e.target.value)}
                className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg"
                placeholder="Reason for transition..."
              />
            </div>
            <button
              type="button"
              onClick={handleTransition}
              disabled={!transitionTarget || !transitionReason}
              className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-chip rounded text-sm font-medium text-white transition-colors"
            >
              Transition
            </button>
          </div>
          {transitionError && <p className="text-red-400 text-sm">{transitionError}</p>}
        </div>
      )}
    </div>
  );
}
