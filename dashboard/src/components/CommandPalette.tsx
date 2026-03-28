import { BookOpen, GitBranch, AlertTriangle, Play, Plug, Plus, Search, Shield } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../lib/api";

interface SearchResult {
  type: string;
  id: string;
  name: string;
  snippet: string;
  status: string;
  url: string;
}

const QUICK_ACTIONS = [
  { id: "new-uc", name: "New Use Case", icon: Plus, url: "/use-cases/new", type: "action" },
  { id: "new-pb", name: "New Playbook", icon: Plus, url: "/playbooks/new", type: "action" },
  { id: "uc-board", name: "Use Case Board", icon: Shield, url: "/use-cases/board", type: "action" },
  { id: "coverage", name: "MITRE Coverage", icon: Shield, url: "/coverage", type: "action" },
];

const TYPE_ICONS: Record<string, typeof Search> = {
  use_case: BookOpen,
  playbook: GitBranch,
  execution: Play,
  alert: AlertTriangle,
  connector: Plug,
  action: Plus,
};

const TYPE_LABELS: Record<string, string> = {
  use_case: "Use Case",
  playbook: "Playbook",
  execution: "Execution",
  alert: "Alert",
  connector: "Connector",
  action: "Quick Action",
};

export default function CommandPalette() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>(undefined);

  // Cmd+K / Ctrl+K to toggle
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery("");
      setResults([]);
      setSelectedIdx(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  // Debounced search
  const doSearch = useCallback(async (q: string) => {
    if (q.length < 2) {
      setResults([]);
      return;
    }
    setLoading(true);
    try {
      const { data } = await api.get("/search", { params: { q, limit: 15 } });
      setResults(data);
      setSelectedIdx(0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInput = (value: string) => {
    setQuery(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(value), 300);
  };

  // Build display list: quick actions (when empty) or search results
  const displayItems: { type: string; id: string; name: string; snippet: string; url: string }[] =
    query.length < 2
      ? QUICK_ACTIONS.map((a) => ({ type: a.type, id: a.id, name: a.name, snippet: "", url: a.url }))
      : results;

  const handleSelect = (item: { url: string }) => {
    setOpen(false);
    navigate(item.url);
  };

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.min(prev + 1, displayItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIdx((prev) => Math.max(prev - 1, 0));
    } else if (e.key === "Enter" && displayItems[selectedIdx]) {
      e.preventDefault();
      handleSelect(displayItems[selectedIdx]);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-overlay" onClick={() => setOpen(false)} />

      {/* Palette */}
      <div className="relative w-full max-w-lg bg-card border border-edge rounded-xl shadow-2xl overflow-hidden">
        {/* Search input */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-edge">
          <Search size={18} className="text-fg3 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search use cases, playbooks, alerts..."
            className="flex-1 bg-transparent text-fg text-sm placeholder-fg3 focus:outline-none"
          />
          <kbd className="text-[10px] text-fg4 border border-edge px-1.5 py-0.5 rounded">ESC</kbd>
        </div>

        {/* Results */}
        <div className="max-h-80 overflow-y-auto">
          {loading && (
            <div className="px-4 py-3 text-sm text-fg3">Searching...</div>
          )}

          {!loading && query.length >= 2 && results.length === 0 && (
            <div className="px-4 py-6 text-center text-fg3 text-sm">
              No results for "{query}"
            </div>
          )}

          {displayItems.map((item, i) => {
            const Icon = TYPE_ICONS[item.type] || Search;
            const label = TYPE_LABELS[item.type] || item.type;
            return (
              <button
                key={item.id}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setSelectedIdx(i)}
                className={`w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors ${
                  i === selectedIdx ? "bg-blue-600/15" : "hover:bg-hover"
                }`}
              >
                <Icon size={16} className="text-fg3 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm text-fg font-medium truncate">{item.name}</div>
                  {item.snippet && (
                    <div className="text-xs text-fg4 truncate">{item.snippet}</div>
                  )}
                </div>
                <span className="text-[10px] text-fg4 bg-chip px-1.5 py-0.5 rounded shrink-0">
                  {label}
                </span>
              </button>
            );
          })}
        </div>

        {/* Footer */}
        <div className="flex items-center gap-4 px-4 py-2 border-t border-edge text-[10px] text-fg4">
          <span>↑↓ Navigate</span>
          <span>↵ Select</span>
          <span>ESC Close</span>
        </div>
      </div>
    </div>
  );
}
