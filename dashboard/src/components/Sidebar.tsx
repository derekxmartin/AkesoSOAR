import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  GitBranch,
  LayoutDashboard,
  Play,
  Plug,
  Settings,
  Shield,
  X,
} from "lucide-react";
import { NavLink } from "react-router-dom";
import { cn } from "../lib/utils";

const NAV_ITEMS = [
  { to: "/", icon: LayoutDashboard, label: "Dashboard" },
  { to: "/use-cases", icon: BookOpen, label: "Use Cases" },
  { to: "/playbooks", icon: GitBranch, label: "Playbooks" },
  { to: "/executions", icon: Play, label: "Executions" },
  { to: "/alerts", icon: AlertTriangle, label: "Alerts" },
  { to: "/coverage", icon: Shield, label: "MITRE Coverage" },
  { to: "/connectors", icon: Plug, label: "Connectors" },
  { to: "/audit-log", icon: BarChart3, label: "Audit Log" },
  { to: "/settings", icon: Settings, label: "Settings" },
];

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
}

export default function Sidebar({ open, onToggle }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && <div className="fixed inset-0 bg-overlay z-30 lg:hidden" onClick={onToggle} />}

      <aside
        className={cn(
          "fixed top-0 left-0 z-40 h-full w-64 bg-nav border-r border-edge transition-transform lg:translate-x-0 lg:static lg:z-auto",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex items-center justify-between h-16 px-4 border-b border-edge">
          <span className="text-lg font-bold text-fg">AkesoSOAR</span>
          <button onClick={onToggle} className="lg:hidden text-fg3 hover:text-fg">
            <X size={20} />
          </button>
        </div>

        <nav className="p-3 space-y-1">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              onClick={() => open && onToggle()}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors",
                  isActive
                    ? "bg-blue-600/20 text-blue-400"
                    : "text-fg2 hover:bg-hover hover:text-fg"
                )
              }
              end={item.to === "/"}
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}
