import * as yaml from "js-yaml";
import { ArrowLeft, Save } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import PlaybookEditor from "../components/PlaybookEditor";
import { useApiGet } from "../hooks/useApiQuery";
import api from "../lib/api";

export default function PlaybookEditPage() {
  const { id } = useParams<{ id: string }>();
  const isNew = !id || id === "new";
  const navigate = useNavigate();

  const { data: existing } = useApiGet<any>(["playbook", id!], `/playbooks/${id}`);

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [triggerType, setTriggerType] = useState("manual");
  const [steps, setSteps] = useState<any[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!isNew && existing) {
      setName(existing.name || "");
      setDescription(existing.description || "");
      setTriggerType(existing.trigger_type || "manual");
      setSteps(existing.definition?.steps || []);
    }
  }, [existing, isNew]);

  const handleSave = async () => {
    setError("");
    setSaving(true);

    const definition = { name, description, steps };
    const yamlStr = yaml.dump(definition, { lineWidth: 120, noRefs: true });

    try {
      if (isNew) {
        const { data } = await api.post("/playbooks", {
          name,
          description,
          yaml_definition: yamlStr,
          trigger_type: triggerType,
        });
        navigate(`/playbooks/${data.id}`);
      } else {
        await api.patch(`/playbooks/${id}`, {
          name,
          description,
          yaml_definition: yamlStr,
          trigger_type: triggerType,
          change_description: "Updated via visual editor",
        });
        navigate(`/playbooks/${id}`);
      }
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === "object" && detail.errors) {
        setError(detail.errors.map((e: any) => e.message).join("; "));
      } else {
        setError(typeof detail === "string" ? detail : "Save failed");
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-4 mb-6">
        <button onClick={() => navigate(isNew ? "/playbooks" : `/playbooks/${id}`)} className="text-fg3 hover:text-fg">
          <ArrowLeft size={20} />
        </button>
        <h1 className="text-2xl font-bold">{isNew ? "New Playbook" : `Edit: ${existing?.name || ""}`}</h1>
      </div>

      <div className="space-y-4 mb-6">
        <div className="grid grid-cols-3 gap-4">
          <div>
            <label className="block text-sm text-fg2 mb-1">Name</label>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-fg2 mb-1">Description</label>
            <input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm text-fg2 mb-1">Trigger Type</label>
            <select
              value={triggerType}
              onChange={(e) => setTriggerType(e.target.value)}
              className="w-full px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg"
            >
              <option value="manual">Manual</option>
              <option value="alert">Alert</option>
              <option value="scheduled">Scheduled</option>
            </select>
          </div>
        </div>
      </div>

      <PlaybookEditor initialSteps={steps} onChange={setSteps} />

      {error && <p className="text-red-400 text-sm mt-4">{error}</p>}

      <button
        onClick={handleSave}
        disabled={saving || !name}
        className="mt-4 flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 rounded-md font-medium text-white transition-colors"
      >
        <Save size={16} /> {saving ? "Saving..." : isNew ? "Create Playbook" : "Save Changes"}
      </button>
    </div>
  );
}
