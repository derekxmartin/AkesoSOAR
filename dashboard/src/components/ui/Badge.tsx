import { cn } from "../../lib/utils";

const VARIANTS: Record<string, string> = {
  draft: "bg-slate-600 text-slate-200",
  testing: "bg-yellow-600/20 text-yellow-400 border border-yellow-600/30",
  production: "bg-green-600/20 text-green-400 border border-green-600/30",
  deprecated: "bg-red-600/20 text-red-400 border border-red-600/30",
  critical: "bg-red-600 text-white",
  high: "bg-orange-600 text-white",
  medium: "bg-yellow-600 text-white",
  low: "bg-blue-600 text-white",
  informational: "bg-slate-600 text-slate-200",
  // execution statuses
  completed: "bg-green-600/20 text-green-400",
  failed: "bg-red-600/20 text-red-400",
  running: "bg-blue-600/20 text-blue-400",
  queued: "bg-slate-600/20 text-slate-400",
  cancelled: "bg-slate-600/20 text-slate-400",
  paused: "bg-yellow-600/20 text-yellow-400",
  success: "bg-green-600/20 text-green-400",
  default: "bg-slate-600 text-slate-200",
};

export default function Badge({ value, className }: { value: string; className?: string }) {
  const variant = VARIANTS[value.toLowerCase()] || VARIANTS.default;
  return (
    <span className={cn("inline-flex px-2 py-0.5 text-xs font-medium rounded-full", variant, className)}>
      {value}
    </span>
  );
}
