import { Bell, CheckCircle, XCircle, AlertTriangle, Clock, Play } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import useWebSocket, { type WsMessage } from "../hooks/useWebSocket";

interface Notification {
  id: string;
  type: string;
  title: string;
  subtitle: string;
  link?: string;
  read: boolean;
  timestamp: string;
}

const TYPE_ICONS: Record<string, typeof Bell> = {
  "human_task.created": AlertTriangle,
  "human_task.approved": CheckCircle,
  "human_task.rejected": XCircle,
  "human_task.timed_out": Clock,
  "execution.paused": Clock,
  "execution.completed": CheckCircle,
  "execution.failed": XCircle,
  "alert.ingested": Play,
};

function formatNotification(msg: WsMessage): Notification | null {
  const id = `${msg.type}-${msg.timestamp || Date.now()}`;
  const ts = msg.timestamp || new Date().toISOString();

  switch (msg.type) {
    case "human_task.created":
      return {
        id,
        type: msg.type,
        title: "Approval Required",
        subtitle: msg.prompt ? `${msg.prompt.slice(0, 80)}` : `Step ${msg.step_id}`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "human_task.approved":
      return {
        id,
        type: msg.type,
        title: "Task Approved",
        subtitle: `Step ${msg.step_id} approved`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "human_task.rejected":
      return {
        id,
        type: msg.type,
        title: "Task Rejected",
        subtitle: `Step ${msg.step_id} rejected`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "human_task.timed_out":
      return {
        id,
        type: msg.type,
        title: "Task Timed Out",
        subtitle: `Step ${msg.step_id} exceeded timeout`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "execution.paused":
      return {
        id,
        type: msg.type,
        title: "Execution Paused",
        subtitle: `Awaiting approval for ${msg.step_id}`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "execution.completed":
      return {
        id,
        type: msg.type,
        title: "Execution Completed",
        subtitle: `Execution finished successfully`,
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    case "execution.failed":
      return {
        id,
        type: msg.type,
        title: "Execution Failed",
        subtitle: msg.reason || "Execution failed",
        link: msg.execution_id ? `/executions/${msg.execution_id}` : undefined,
        read: false,
        timestamp: ts,
      };
    default:
      return null;
  }
}

export default function NotificationCenter() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const onMessage = useCallback((msg: WsMessage) => {
    const notif = formatNotification(msg);
    if (notif) {
      setNotifications((prev) => [notif, ...prev].slice(0, 50));
    }
  }, []);

  useWebSocket({ onMessage });

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const handleClick = (notif: Notification) => {
    // Mark as read
    setNotifications((prev) =>
      prev.map((n) => (n.id === notif.id ? { ...n, read: true } : n))
    );
    if (notif.link) {
      navigate(notif.link);
      setOpen(false);
    }
  };

  const timeAgo = (ts: string) => {
    const diff = Date.now() - new Date(ts).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative p-1.5 rounded-md text-fg3 hover:text-fg hover:bg-hover transition-colors"
        title="Notifications"
      >
        <Bell size={18} />
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[10px] font-bold rounded-full min-w-[16px] h-4 flex items-center justify-center px-1">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-10 w-80 bg-card border border-edge rounded-lg shadow-xl z-50 overflow-hidden">
          <div className="flex items-center justify-between px-3 py-2 border-b border-edge">
            <span className="text-sm font-semibold text-fg">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto">
            {notifications.length === 0 ? (
              <div className="px-3 py-8 text-center text-fg3 text-sm">
                No notifications yet
              </div>
            ) : (
              notifications.map((notif) => {
                const Icon = TYPE_ICONS[notif.type] || Bell;
                const isError = notif.type.includes("failed") || notif.type.includes("rejected") || notif.type.includes("timed_out");
                const isSuccess = notif.type.includes("approved") || notif.type.includes("completed");

                return (
                  <button
                    key={notif.id}
                    onClick={() => handleClick(notif)}
                    className={`w-full flex items-start gap-2.5 px-3 py-2.5 text-left hover:bg-hover transition-colors border-b border-edge-a ${
                      !notif.read ? "bg-blue-500/5" : ""
                    }`}
                  >
                    <Icon
                      size={16}
                      className={`mt-0.5 shrink-0 ${
                        isError ? "text-red-400" : isSuccess ? "text-green-400" : "text-yellow-400"
                      }`}
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`text-xs font-medium ${!notif.read ? "text-fg" : "text-fg2"}`}>
                          {notif.title}
                        </span>
                        {!notif.read && (
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-400 shrink-0" />
                        )}
                      </div>
                      <p className="text-[11px] text-fg3 truncate">{notif.subtitle}</p>
                      <span className="text-[10px] text-fg4">{timeAgo(notif.timestamp)}</span>
                    </div>
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}
    </div>
  );
}
