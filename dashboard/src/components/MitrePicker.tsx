import { useState } from "react";
import { cn } from "../lib/utils";

// Comprehensive MITRE ATT&CK techniques — matches backend mitre_coverage.py
// ~300 techniques across 12 actionable tactics (excludes Reconnaissance & Resource Development)
const TECHNIQUES: Record<string, { name: string; tactics: string[] }> = {
  // TA0001 — Initial Access
  T1189: { name: "Drive-by Compromise", tactics: ["TA0001"] },
  T1190: { name: "Exploit Public-Facing Application", tactics: ["TA0001"] },
  T1133: { name: "External Remote Services", tactics: ["TA0001", "TA0003"] },
  T1091: { name: "Replication Through Removable Media", tactics: ["TA0001", "TA0008"] },
  T1195: { name: "Supply Chain Compromise", tactics: ["TA0001"] },
  "T1195.001": { name: "Compromise Software Dependencies", tactics: ["TA0001"] },
  "T1195.002": { name: "Compromise Software Supply Chain", tactics: ["TA0001"] },
  T1199: { name: "Trusted Relationship", tactics: ["TA0001"] },
  T1078: { name: "Valid Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },
  "T1078.001": { name: "Default Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },
  "T1078.002": { name: "Domain Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },
  "T1078.003": { name: "Local Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },
  "T1078.004": { name: "Cloud Accounts", tactics: ["TA0001", "TA0003", "TA0004", "TA0005"] },

  // TA0002 — Execution
  T1059: { name: "Command and Scripting Interpreter", tactics: ["TA0002"] },
  "T1059.001": { name: "PowerShell", tactics: ["TA0002"] },
  "T1059.003": { name: "Windows Command Shell", tactics: ["TA0002"] },
  "T1059.004": { name: "Unix Shell", tactics: ["TA0002"] },
  "T1059.005": { name: "Visual Basic", tactics: ["TA0002"] },
  "T1059.006": { name: "Python", tactics: ["TA0002"] },
  "T1059.007": { name: "JavaScript", tactics: ["TA0002"] },
  "T1059.008": { name: "Network Device CLI", tactics: ["TA0002"] },
  "T1059.009": { name: "Cloud API", tactics: ["TA0002"] },
  T1203: { name: "Exploitation for Client Execution", tactics: ["TA0002"] },
  T1559: { name: "Inter-Process Communication", tactics: ["TA0002"] },
  "T1559.001": { name: "Component Object Model", tactics: ["TA0002"] },
  "T1559.002": { name: "Dynamic Data Exchange", tactics: ["TA0002"] },
  T1106: { name: "Native API", tactics: ["TA0002"] },
  T1053: { name: "Scheduled Task/Job", tactics: ["TA0002", "TA0003", "TA0004"] },
  "T1053.005": { name: "Scheduled Task", tactics: ["TA0002", "TA0003", "TA0004"] },
  "T1053.003": { name: "Cron", tactics: ["TA0002", "TA0003", "TA0004"] },
  T1072: { name: "Software Deployment Tools", tactics: ["TA0002", "TA0008"] },
  T1569: { name: "System Services", tactics: ["TA0002"] },
  "T1569.002": { name: "Service Execution", tactics: ["TA0002"] },
  T1204: { name: "User Execution", tactics: ["TA0002"] },
  "T1204.002": { name: "Malicious File", tactics: ["TA0002"] },
  T1047: { name: "Windows Management Instrumentation", tactics: ["TA0002"] },
  T1651: { name: "Cloud Administration Command", tactics: ["TA0002"] },

  // TA0003 — Persistence
  T1098: { name: "Account Manipulation", tactics: ["TA0003", "TA0004"] },
  "T1098.001": { name: "Additional Cloud Credentials", tactics: ["TA0003", "TA0004"] },
  "T1098.004": { name: "SSH Authorized Keys", tactics: ["TA0003", "TA0004"] },
  T1197: { name: "BITS Jobs", tactics: ["TA0003", "TA0005"] },
  T1547: { name: "Boot or Logon Autostart Execution", tactics: ["TA0003", "TA0004"] },
  "T1547.001": { name: "Registry Run Keys / Startup Folder", tactics: ["TA0003", "TA0004"] },
  "T1547.004": { name: "Winlogon Helper DLL", tactics: ["TA0003", "TA0004"] },
  "T1547.006": { name: "Kernel Modules and Extensions", tactics: ["TA0003", "TA0004"] },
  "T1547.009": { name: "Shortcut Modification", tactics: ["TA0003", "TA0004"] },
  T1037: { name: "Boot or Logon Initialization Scripts", tactics: ["TA0003", "TA0004"] },
  T1136: { name: "Create Account", tactics: ["TA0003"] },
  "T1136.001": { name: "Local Account", tactics: ["TA0003"] },
  "T1136.002": { name: "Domain Account", tactics: ["TA0003"] },
  "T1136.003": { name: "Cloud Account", tactics: ["TA0003"] },
  T1543: { name: "Create or Modify System Process", tactics: ["TA0003", "TA0004"] },
  "T1543.003": { name: "Windows Service", tactics: ["TA0003", "TA0004"] },
  T1546: { name: "Event Triggered Execution", tactics: ["TA0003", "TA0004"] },
  "T1546.003": { name: "WMI Event Subscription", tactics: ["TA0003", "TA0004"] },
  "T1546.008": { name: "Accessibility Features", tactics: ["TA0003", "TA0004"] },
  "T1546.012": { name: "Image File Execution Options Injection", tactics: ["TA0003", "TA0004"] },
  "T1546.015": { name: "COM Hijacking", tactics: ["TA0003", "TA0004"] },
  T1574: { name: "Hijack Execution Flow", tactics: ["TA0003", "TA0004", "TA0005"] },
  "T1574.001": { name: "DLL Search Order Hijacking", tactics: ["TA0003", "TA0004", "TA0005"] },
  "T1574.002": { name: "DLL Side-Loading", tactics: ["TA0003", "TA0004", "TA0005"] },
  T1556: { name: "Modify Authentication Process", tactics: ["TA0003", "TA0005", "TA0006"] },
  T1112: { name: "Modify Registry", tactics: ["TA0003", "TA0005"] },
  T1505: { name: "Server Software Component", tactics: ["TA0003"] },
  "T1505.003": { name: "Web Shell", tactics: ["TA0003"] },
  T1176: { name: "Software Extensions", tactics: ["TA0003"] },
  T1554: { name: "Compromise Host Software Binary", tactics: ["TA0003"] },

  // TA0004 — Privilege Escalation
  T1548: { name: "Abuse Elevation Control Mechanism", tactics: ["TA0004", "TA0005"] },
  "T1548.002": { name: "Bypass User Account Control", tactics: ["TA0004", "TA0005"] },
  "T1548.003": { name: "Sudo and Sudo Caching", tactics: ["TA0004", "TA0005"] },
  T1134: { name: "Access Token Manipulation", tactics: ["TA0004", "TA0005"] },
  "T1134.001": { name: "Token Impersonation/Theft", tactics: ["TA0004", "TA0005"] },
  "T1134.002": { name: "Create Process with Token", tactics: ["TA0004", "TA0005"] },
  "T1134.005": { name: "SID-History Injection", tactics: ["TA0004", "TA0005"] },
  T1484: { name: "Domain or Tenant Policy Modification", tactics: ["TA0004", "TA0005"] },
  "T1484.001": { name: "Group Policy Modification", tactics: ["TA0004", "TA0005"] },
  T1611: { name: "Escape to Host", tactics: ["TA0004"] },
  T1068: { name: "Exploitation for Privilege Escalation", tactics: ["TA0004"] },
  T1055: { name: "Process Injection", tactics: ["TA0004", "TA0005"] },
  "T1055.001": { name: "DLL Injection", tactics: ["TA0004", "TA0005"] },
  "T1055.012": { name: "Process Hollowing", tactics: ["TA0004", "TA0005"] },

  // TA0005 — Defense Evasion
  T1140: { name: "Deobfuscate/Decode Files", tactics: ["TA0005"] },
  T1006: { name: "Direct Volume Access", tactics: ["TA0005"] },
  T1222: { name: "File and Directory Permissions Modification", tactics: ["TA0005"] },
  T1564: { name: "Hide Artifacts", tactics: ["TA0005"] },
  "T1564.001": { name: "Hidden Files and Directories", tactics: ["TA0005"] },
  "T1564.004": { name: "NTFS File Attributes", tactics: ["TA0005"] },
  T1562: { name: "Impair Defenses", tactics: ["TA0005"] },
  "T1562.001": { name: "Disable or Modify Tools", tactics: ["TA0005"] },
  "T1562.002": { name: "Disable Windows Event Logging", tactics: ["TA0005"] },
  "T1562.004": { name: "Disable or Modify System Firewall", tactics: ["TA0005"] },
  "T1562.007": { name: "Disable or Modify Cloud Firewall", tactics: ["TA0005"] },
  T1070: { name: "Indicator Removal", tactics: ["TA0005"] },
  "T1070.001": { name: "Clear Windows Event Logs", tactics: ["TA0005"] },
  "T1070.004": { name: "File Deletion", tactics: ["TA0005"] },
  "T1070.006": { name: "Timestomp", tactics: ["TA0005"] },
  T1202: { name: "Indirect Command Execution", tactics: ["TA0005"] },
  T1036: { name: "Masquerading", tactics: ["TA0005"] },
  "T1036.005": { name: "Match Legitimate Name or Location", tactics: ["TA0005"] },
  T1027: { name: "Obfuscated Files or Information", tactics: ["TA0005"] },
  "T1027.002": { name: "Software Packing", tactics: ["TA0005"] },
  "T1027.006": { name: "HTML Smuggling", tactics: ["TA0005"] },
  "T1027.010": { name: "Command Obfuscation", tactics: ["TA0005"] },
  "T1027.011": { name: "Fileless Storage", tactics: ["TA0005"] },
  T1014: { name: "Rootkit", tactics: ["TA0005"] },
  T1218: { name: "System Binary Proxy Execution", tactics: ["TA0005"] },
  "T1218.005": { name: "Mshta", tactics: ["TA0005"] },
  "T1218.010": { name: "Regsvr32", tactics: ["TA0005"] },
  "T1218.011": { name: "Rundll32", tactics: ["TA0005"] },
  T1127: { name: "Trusted Developer Utilities", tactics: ["TA0005"] },
  "T1127.001": { name: "MSBuild", tactics: ["TA0005"] },
  T1550: { name: "Use Alternate Authentication Material", tactics: ["TA0005", "TA0008"] },
  "T1550.002": { name: "Pass the Hash", tactics: ["TA0005", "TA0008"] },
  "T1550.003": { name: "Pass the Ticket", tactics: ["TA0005", "TA0008"] },
  T1497: { name: "Virtualization/Sandbox Evasion", tactics: ["TA0005", "TA0007"] },
  T1220: { name: "XSL Script Processing", tactics: ["TA0005"] },
  T1620: { name: "Reflective Code Loading", tactics: ["TA0005"] },

  // TA0006 — Credential Access
  T1557: { name: "Adversary-in-the-Middle", tactics: ["TA0006", "TA0009"] },
  "T1557.001": { name: "LLMNR/NBT-NS Poisoning", tactics: ["TA0006", "TA0009"] },
  T1110: { name: "Brute Force", tactics: ["TA0006"] },
  "T1110.001": { name: "Password Guessing", tactics: ["TA0006"] },
  "T1110.003": { name: "Password Spraying", tactics: ["TA0006"] },
  "T1110.004": { name: "Credential Stuffing", tactics: ["TA0006"] },
  T1555: { name: "Credentials from Password Stores", tactics: ["TA0006"] },
  "T1555.003": { name: "Credentials from Web Browsers", tactics: ["TA0006"] },
  T1212: { name: "Exploitation for Credential Access", tactics: ["TA0006"] },
  T1187: { name: "Forced Authentication", tactics: ["TA0006"] },
  T1606: { name: "Forge Web Credentials", tactics: ["TA0006"] },
  "T1606.002": { name: "SAML Tokens", tactics: ["TA0006"] },
  T1056: { name: "Input Capture", tactics: ["TA0006", "TA0009"] },
  "T1056.001": { name: "Keylogging", tactics: ["TA0006", "TA0009"] },
  T1621: { name: "MFA Request Generation", tactics: ["TA0006"] },
  T1040: { name: "Network Sniffing", tactics: ["TA0006", "TA0007"] },
  T1003: { name: "OS Credential Dumping", tactics: ["TA0006"] },
  "T1003.001": { name: "LSASS Memory", tactics: ["TA0006"] },
  "T1003.002": { name: "Security Account Manager", tactics: ["TA0006"] },
  "T1003.003": { name: "NTDS", tactics: ["TA0006"] },
  "T1003.006": { name: "DCSync", tactics: ["TA0006"] },
  T1558: { name: "Steal or Forge Kerberos Tickets", tactics: ["TA0006"] },
  "T1558.001": { name: "Golden Ticket", tactics: ["TA0006"] },
  "T1558.003": { name: "Kerberoasting", tactics: ["TA0006"] },
  "T1558.004": { name: "AS-REP Roasting", tactics: ["TA0006"] },
  T1539: { name: "Steal Web Session Cookie", tactics: ["TA0006"] },
  T1552: { name: "Unsecured Credentials", tactics: ["TA0006"] },
  "T1552.001": { name: "Credentials In Files", tactics: ["TA0006"] },
  "T1552.004": { name: "Private Keys", tactics: ["TA0006"] },

  // TA0007 — Discovery
  T1087: { name: "Account Discovery", tactics: ["TA0007"] },
  "T1087.001": { name: "Local Account", tactics: ["TA0007"] },
  "T1087.002": { name: "Domain Account", tactics: ["TA0007"] },
  T1482: { name: "Domain Trust Discovery", tactics: ["TA0007"] },
  T1083: { name: "File and Directory Discovery", tactics: ["TA0007"] },
  T1046: { name: "Network Service Discovery", tactics: ["TA0007"] },
  T1135: { name: "Network Share Discovery", tactics: ["TA0007"] },
  T1069: { name: "Permission Groups Discovery", tactics: ["TA0007"] },
  T1057: { name: "Process Discovery", tactics: ["TA0007"] },
  T1018: { name: "Remote System Discovery", tactics: ["TA0007"] },
  T1518: { name: "Software Discovery", tactics: ["TA0007"] },
  "T1518.001": { name: "Security Software Discovery", tactics: ["TA0007"] },
  T1082: { name: "System Information Discovery", tactics: ["TA0007"] },
  T1016: { name: "System Network Configuration Discovery", tactics: ["TA0007"] },
  T1049: { name: "System Network Connections Discovery", tactics: ["TA0007"] },
  T1033: { name: "System Owner/User Discovery", tactics: ["TA0007"] },

  // TA0008 — Lateral Movement
  T1210: { name: "Exploitation of Remote Services", tactics: ["TA0008"] },
  T1534: { name: "Internal Spearphishing", tactics: ["TA0008"] },
  T1570: { name: "Lateral Tool Transfer", tactics: ["TA0008"] },
  T1563: { name: "Remote Service Session Hijacking", tactics: ["TA0008"] },
  "T1563.002": { name: "RDP Hijacking", tactics: ["TA0008"] },
  T1021: { name: "Remote Services", tactics: ["TA0008"] },
  "T1021.001": { name: "Remote Desktop Protocol", tactics: ["TA0008"] },
  "T1021.002": { name: "SMB/Windows Admin Shares", tactics: ["TA0008"] },
  "T1021.004": { name: "SSH", tactics: ["TA0008"] },
  "T1021.006": { name: "Windows Remote Management", tactics: ["TA0008"] },
  T1080: { name: "Taint Shared Content", tactics: ["TA0008"] },

  // TA0009 — Collection
  T1560: { name: "Archive Collected Data", tactics: ["TA0009"] },
  T1119: { name: "Automated Collection", tactics: ["TA0009"] },
  T1115: { name: "Clipboard Data", tactics: ["TA0009"] },
  T1530: { name: "Data from Cloud Storage", tactics: ["TA0009"] },
  T1213: { name: "Data from Information Repositories", tactics: ["TA0009"] },
  T1005: { name: "Data from Local System", tactics: ["TA0009"] },
  T1039: { name: "Data from Network Shared Drive", tactics: ["TA0009"] },
  T1074: { name: "Data Staged", tactics: ["TA0009"] },
  T1114: { name: "Email Collection", tactics: ["TA0009"] },
  "T1114.003": { name: "Email Forwarding Rule", tactics: ["TA0009"] },
  T1113: { name: "Screen Capture", tactics: ["TA0009"] },

  // TA0010 — Exfiltration
  T1020: { name: "Automated Exfiltration", tactics: ["TA0010"] },
  T1048: { name: "Exfiltration Over Alternative Protocol", tactics: ["TA0010"] },
  T1041: { name: "Exfiltration Over C2 Channel", tactics: ["TA0010"] },
  T1567: { name: "Exfiltration Over Web Service", tactics: ["TA0010"] },
  "T1567.002": { name: "Exfiltration to Cloud Storage", tactics: ["TA0010"] },
  T1029: { name: "Scheduled Transfer", tactics: ["TA0010"] },
  T1537: { name: "Transfer Data to Cloud Account", tactics: ["TA0010"] },

  // TA0011 — Command and Control
  T1071: { name: "Application Layer Protocol", tactics: ["TA0011"] },
  "T1071.001": { name: "Web Protocols", tactics: ["TA0011"] },
  "T1071.004": { name: "DNS", tactics: ["TA0011"] },
  T1132: { name: "Data Encoding", tactics: ["TA0011"] },
  T1001: { name: "Data Obfuscation", tactics: ["TA0011"] },
  T1568: { name: "Dynamic Resolution", tactics: ["TA0011"] },
  "T1568.002": { name: "Domain Generation Algorithms", tactics: ["TA0011"] },
  T1573: { name: "Encrypted Channel", tactics: ["TA0011"] },
  T1008: { name: "Fallback Channels", tactics: ["TA0011"] },
  T1105: { name: "Ingress Tool Transfer", tactics: ["TA0011"] },
  T1095: { name: "Non-Application Layer Protocol", tactics: ["TA0011"] },
  T1571: { name: "Non-Standard Port", tactics: ["TA0011"] },
  T1572: { name: "Protocol Tunneling", tactics: ["TA0011"] },
  T1090: { name: "Proxy", tactics: ["TA0011"] },
  "T1090.003": { name: "Multi-hop Proxy", tactics: ["TA0011"] },
  T1219: { name: "Remote Access Tools", tactics: ["TA0011"] },
  T1102: { name: "Web Service", tactics: ["TA0011"] },

  // TA0040 — Impact
  T1531: { name: "Account Access Removal", tactics: ["TA0040"] },
  T1485: { name: "Data Destruction", tactics: ["TA0040"] },
  T1486: { name: "Data Encrypted for Impact", tactics: ["TA0040"] },
  T1565: { name: "Data Manipulation", tactics: ["TA0040"] },
  T1491: { name: "Defacement", tactics: ["TA0040"] },
  T1561: { name: "Disk Wipe", tactics: ["TA0040"] },
  T1499: { name: "Endpoint Denial of Service", tactics: ["TA0040"] },
  T1495: { name: "Firmware Corruption", tactics: ["TA0040"] },
  T1490: { name: "Inhibit System Recovery", tactics: ["TA0040"] },
  T1498: { name: "Network Denial of Service", tactics: ["TA0040"] },
  T1496: { name: "Resource Hijacking", tactics: ["TA0040"] },
  T1489: { name: "Service Stop", tactics: ["TA0040"] },
  T1529: { name: "System Shutdown/Reboot", tactics: ["TA0040"] },
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
};

interface Props {
  selectedTactics: string[];
  selectedTechniques: string[];
  onTacticsChange: (tactics: string[]) => void;
  onTechniquesChange: (techniques: string[]) => void;
}

export default function MitrePicker({ selectedTactics, selectedTechniques, onTacticsChange, onTechniquesChange }: Props) {
  const [search, setSearch] = useState("");
  const [tacticFilter, setTacticFilter] = useState("");

  const filteredTechniques = Object.entries(TECHNIQUES).filter(
    ([id, t]) => {
      const matchesSearch = !search ||
        id.toLowerCase().includes(search.toLowerCase()) ||
        t.name.toLowerCase().includes(search.toLowerCase());
      const matchesTactic = !tacticFilter || t.tactics.includes(tacticFilter);
      return matchesSearch && matchesTactic;
    }
  );

  const toggleTechnique = (id: string) => {
    const t = TECHNIQUES[id];
    if (selectedTechniques.includes(id)) {
      onTechniquesChange(selectedTechniques.filter((x) => x !== id));
    } else {
      onTechniquesChange([...selectedTechniques, id]);
      for (const tactic of t.tactics) {
        if (!selectedTactics.includes(tactic)) {
          onTacticsChange([...selectedTactics, tactic]);
        }
      }
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex gap-2">
        <input
          type="text"
          placeholder="Search techniques (e.g., T1110, Brute Force)..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg placeholder-fg3 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <select
          value={tacticFilter}
          onChange={(e) => setTacticFilter(e.target.value)}
          className="px-3 py-2 bg-inset border border-edge2 rounded text-sm text-fg"
        >
          <option value="">All Tactics</option>
          {Object.entries(TACTICS).map(([id, name]) => (
            <option key={id} value={id}>{name}</option>
          ))}
        </select>
      </div>
      <div className="text-xs text-fg4">{filteredTechniques.length} techniques shown · {Object.keys(TECHNIQUES).length} total</div>
      <div className="max-h-64 overflow-y-auto space-y-1">
        {filteredTechniques.map(([id, t]) => (
          <label
            key={id}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded cursor-pointer text-sm",
              selectedTechniques.includes(id) ? "bg-blue-600/20 text-blue-300" : "hover:bg-hover-row text-fg2"
            )}
          >
            <input
              type="checkbox"
              checked={selectedTechniques.includes(id)}
              onChange={() => toggleTechnique(id)}
              className="rounded"
            />
            <span className="font-mono text-xs text-fg3 w-20 shrink-0">{id}</span>
            <span className="truncate">{t.name}</span>
            <span className="ml-auto text-xs text-fg4 shrink-0">{t.tactics.map((ta) => TACTICS[ta]).join(", ")}</span>
          </label>
        ))}
      </div>
      {selectedTechniques.length > 0 && (
        <div className="text-xs text-fg3">
          {selectedTechniques.length} technique(s) selected | Tactics: {selectedTactics.join(", ")}
        </div>
      )}
    </div>
  );
}
