import { LogOut, Menu } from "lucide-react";
import { useState } from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import Sidebar from "./Sidebar";

export default function AppShell() {
  const { isAuthenticated, user, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <Sidebar open={sidebarOpen} onToggle={() => setSidebarOpen(!sidebarOpen)} />

      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-slate-700 bg-slate-900 shrink-0">
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="lg:hidden text-slate-400 hover:text-white"
          >
            <Menu size={20} />
          </button>

          <div className="flex-1" />

          <div className="flex items-center gap-4">
            <div className="text-sm">
              <span className="text-slate-400">Signed in as </span>
              <span className="font-medium text-white">{user?.username}</span>
              <span className="ml-2 text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
                {user?.role}
              </span>
            </div>
            <button
              onClick={logout}
              className="text-slate-400 hover:text-red-400 transition-colors"
              title="Logout"
            >
              <LogOut size={18} />
            </button>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
