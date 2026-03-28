import { useState, useRef, useEffect, type ReactNode } from "react";
import { HelpCircle } from "lucide-react";

interface TooltipProps {
  text: string;
  children?: ReactNode;
}

export default function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState<"above" | "below">("above");
  const iconRef = useRef<HTMLSpanElement>(null);
  const tipRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (visible && iconRef.current) {
      const rect = iconRef.current.getBoundingClientRect();
      // If not enough room above, show below
      setPosition(rect.top < 60 ? "below" : "above");
    }
  }, [visible]);

  return (
    <span className="relative inline-flex items-center">
      {children}
      <span
        ref={iconRef}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        className="ml-1 text-slate-500 hover:text-blue-400 cursor-help inline-flex"
      >
        <HelpCircle size={12} />
      </span>
      {visible && (
        <div
          ref={tipRef}
          className={`absolute z-50 left-1/2 -translate-x-1/2 px-2.5 py-1.5 bg-slate-950 border border-slate-600 rounded shadow-lg text-[11px] text-slate-300 leading-relaxed w-56 pointer-events-none ${
            position === "above" ? "bottom-full mb-1.5" : "top-full mt-1.5"
          }`}
        >
          {text}
          <div
            className={`absolute left-1/2 -translate-x-1/2 w-2 h-2 bg-slate-950 border-slate-600 rotate-45 ${
              position === "above"
                ? "top-full -mt-1 border-r border-b"
                : "bottom-full -mb-1 border-l border-t"
            }`}
          />
        </div>
      )}
    </span>
  );
}

/** Convenience: label text + tooltip icon inline */
export function FieldLabel({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <label className="flex items-center text-xs text-slate-400 mb-1">
      <Tooltip text={tooltip}>
        <span>{label}</span>
      </Tooltip>
    </label>
  );
}
