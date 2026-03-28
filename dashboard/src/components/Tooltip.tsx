import { useState, useRef, useCallback, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { HelpCircle } from "lucide-react";

interface TooltipProps {
  text: string;
  children?: ReactNode;
}

export default function Tooltip({ text, children }: TooltipProps) {
  const [visible, setVisible] = useState(false);
  const [coords, setCoords] = useState({ x: 0, y: 0, placement: "above" as "above" | "below" });
  const iconRef = useRef<HTMLSpanElement>(null);

  const show = useCallback(() => {
    if (!iconRef.current) return;
    const rect = iconRef.current.getBoundingClientRect();
    const tipWidth = 224; // w-56 = 14rem = 224px
    const tipHeight = 80; // rough estimate

    // Horizontal: center on icon, clamp to viewport
    let x = rect.left + rect.width / 2 - tipWidth / 2;
    x = Math.max(8, Math.min(x, window.innerWidth - tipWidth - 8));

    // Vertical: prefer above, fall back to below
    let placement: "above" | "below" = "above";
    let y = rect.top - tipHeight - 6;
    if (y < 8) {
      placement = "below";
      y = rect.bottom + 6;
    }

    setCoords({ x, y, placement });
    setVisible(true);
  }, []);

  return (
    <span className="relative inline-flex items-center">
      {children}
      <span
        ref={iconRef}
        onMouseEnter={show}
        onMouseLeave={() => setVisible(false)}
        className="ml-1 text-fg4 hover:text-blue-400 cursor-help inline-flex"
      >
        <HelpCircle size={12} />
      </span>
      {visible &&
        createPortal(
          <div
            style={{
              position: "fixed",
              left: coords.x,
              top: coords.y,
              zIndex: 9999,
              width: 224,
            }}
            className="px-2.5 py-1.5 bg-app border border-edge2 rounded shadow-xl text-[11px] text-fg2 leading-relaxed pointer-events-none"
          >
            {text}
          </div>,
          document.body
        )}
    </span>
  );
}

/** Convenience: label text + tooltip icon inline */
export function FieldLabel({ label, tooltip }: { label: string; tooltip: string }) {
  return (
    <label className="flex items-center text-xs text-fg3 mb-1">
      <Tooltip text={tooltip}>
        <span>{label}</span>
      </Tooltip>
    </label>
  );
}
