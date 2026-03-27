import { useState } from "react";
import { cn } from "../lib/utils";

// Subset of MITRE ATT&CK techniques (matches the backend mitre_coverage.py)
const TECHNIQUES: Record<string, { name: string; tactics: string[] }> = {
  T1059: { name: "Command and Scripting Interpreter", tactics: ["TA0002"] },
  "T1059.001": { name: "PowerShell", tactics: ["TA0002"] },
  "T1059.003": { name: "Windows Command Shell", tactics: ["TA0002"] },
  T1078: { name: "Valid Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },
  T1110: { name: "Brute Force", tactics: ["TA0006"] },
  "T1110.001": { name: "Password Guessing", tactics: ["TA0006"] },
  "T1110.003": { name: "Password Spraying", tactics: ["TA0006"] },
  T1003: { name: "OS Credential Dumping", tactics: ["TA0006"] },
  "T1003.001": { name: "LSASS Memory", tactics: ["TA0006"] },
  T1021: { name: "Remote Services", tactics: ["TA0008"] },
  "T1021.001": { name: "Remote Desktop Protocol", tactics: ["TA0008"] },
  T1053: { name: "Scheduled Task/Job", tactics: ["TA0002", "TA0003"] },
  T1071: { name: "Application Layer Protocol", tactics: ["TA0011"] },
  T1486: { name: "Data Encrypted for Impact", tactics: ["TA0040"] },
  T1566: { name: "Phishing", tactics: ["TA0001"] },
  "T1566.001": { name: "Spearphishing Attachment", tactics: ["TA0001"] },
  "T1566.002": { name: "Spearphishing Link", tactics: ["TA0001"] },
  T1547: { name: "Boot or Logon Autostart Execution", tactics: ["TA0003"] },
  T1048: { name: "Exfiltration Over Alternative Protocol", tactics: ["TA0010"] },
  T1082: { name: "System Information Discovery", tactics: ["TA0007"] },
  T1005: { name: "Data from Local System", tactics: ["TA0009"] },
  T1595: { name: "Active Scanning", tactics: ["TA0043"] },
};

const TACTICS: Record<string, string> = {
  TA0001: "Initial Access",
  TA0002: "Execution",
  TA0003: "Persistence",
  TA0004: "Privilege Escalation",
  TA0005: "Defense Evasion",
  TA0006: "Credential Access",
  TA0007: "Discovery",
  TA0008: "Lateral Movement",
  TA0009: "Collection",
  TA0010: "Exfiltration",
  TA0011: "Command and Control",
  TA0040: "Impact",
  TA0042: "Resource Development",
  TA0043: "Reconnaissance",
};

interface Props {
  selectedTactics: string[];
  selectedTechniques: string[];
  onTacticsChange: (tactics: string[]) => void;
  onTechniquesChange: (techniques: string[]) => void;
}

export default function MitrePicker({ selectedTactics, selectedTechniques, onTacticsChange, onTechniquesChange }: Props) {
  const [search, setSearch] = useState("");

  const filteredTechniques = Object.entries(TECHNIQUES).filter(
    ([id, t]) =>
      id.toLowerCase().includes(search.toLowerCase()) ||
      t.name.toLowerCase().includes(search.toLowerCase())
  );

  const toggleTechnique = (id: string) => {
    const t = TECHNIQUES[id];
    if (selectedTechniques.includes(id)) {
      onTechniquesChange(selectedTechniques.filter((x) => x !== id));
    } else {
      onTechniquesChange([...selectedTechniques, id]);
      // Auto-add parent tactics
      for (const tactic of t.tactics) {
        if (!selectedTactics.includes(tactic)) {
          onTacticsChange([...selectedTactics, tactic]);
        }
      }
    }
  };

  return (
    <div className="space-y-3">
      <input
        type="text"
        placeholder="Search techniques (e.g., T1110, Brute Force)..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
      />
      <div className="max-h-64 overflow-y-auto space-y-1">
        {filteredTechniques.map(([id, t]) => (
          <label
            key={id}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded cursor-pointer text-sm",
              selectedTechniques.includes(id) ? "bg-blue-600/20 text-blue-300" : "hover:bg-slate-700/50 text-slate-300"
            )}
          >
            <input
              type="checkbox"
              checked={selectedTechniques.includes(id)}
              onChange={() => toggleTechnique(id)}
              className="rounded"
            />
            <span className="font-mono text-xs text-slate-400 w-20">{id}</span>
            <span>{t.name}</span>
            <span className="ml-auto text-xs text-slate-500">{t.tactics.map((ta) => TACTICS[ta]).join(", ")}</span>
          </label>
        ))}
      </div>
      {selectedTechniques.length > 0 && (
        <div className="text-xs text-slate-400">
          {selectedTechniques.length} technique(s) selected | Tactics: {selectedTactics.join(", ")}
        </div>
      )}
    </div>
  );
}
