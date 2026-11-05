import { NavLink } from "react-router-dom";
import { useState } from "react";
import { LayoutDashboard, Boxes, History, Settings, ShieldCheck, Trash2, Users, LogOut, RefreshCw } from "lucide-react";
import { AuthUser } from "../types";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/models", label: "Models", icon: Boxes },
  { to: "/history", label: "History", icon: History },
  { to: "/trash", label: "Thùng rác", icon: Trash2 },
  { to: "/settings", label: "Settings", icon: Settings },
  { to: "/users", label: "Users", icon: Users, adminOnly: true },
];

export default function Sidebar({ user, onSignOut }: { user: AuthUser; onSignOut: () => Promise<void> }) {
  const [refreshing, setRefreshing] = useState(false);
  const navItems = NAV_ITEMS.filter((item) => !item.adminOnly || user.role === "admin");

  const refreshApplication = async () => {
    if (refreshing) return;
    setRefreshing(true);

    try {
      if ("serviceWorker" in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.update().catch(() => undefined)));
      }

      if ("caches" in window) {
        const cacheNames = await caches.keys();
        await Promise.all(
          cacheNames
            .filter((cacheName) => cacheName.startsWith("model-restore-"))
            .map((cacheName) => caches.delete(cacheName))
        );
      }

      window.location.reload();
    } catch {
      window.location.reload();
    }
  };

  const refreshButton = (compact = false) => (
    <button
      type="button"
      onClick={() => void refreshApplication()}
      disabled={refreshing}
      aria-label="Refresh app to load updates"
      title="Refresh app to load updates"
      className={`flex items-center justify-center gap-2 rounded-md text-zinc-400 transition-colors hover:bg-white/[0.06] hover:text-white disabled:opacity-60 ${compact ? "h-8 w-8 shrink-0" : "w-full px-3 py-2 text-xs"}`}
    >
      <RefreshCw size={15} className={refreshing ? "animate-spin" : ""} aria-hidden="true" />
      {!compact && <span>{refreshing ? "Updating..." : "Refresh app"}</span>}
    </button>
  );

  return (
    <aside className="premium-sidebar sticky top-0 z-20 flex w-full shrink-0 flex-col border-b border-border backdrop-blur-md md:h-full md:w-60 md:border-b-0 md:border-r lg:w-64">
      <div className="flex items-center gap-2.5 px-4 py-3 md:px-5 md:py-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-400/30 bg-slate-500/10 shadow-[0_0_24px_rgba(148,163,184,0.14)]">
          <img src="/logo.svg" alt="" className="h-7 w-7 shrink-0" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold leading-tight text-white">Model Khôi Phục Chữ Viết</p>
          <p className="text-xs leading-tight text-muted">Khôi phục chữ trong ảnh</p>
        </div>
        <div className="flex shrink-0 items-center gap-1 md:hidden">
          {refreshButton(true)}
          <button type="button" onClick={() => void onSignOut()} aria-label="Sign out" title="Sign out" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-400 hover:bg-white/[0.06] hover:text-white">
            <LogOut size={15} />
          </button>
        </div>
      </div>

      <nav className="flex gap-1 overflow-x-auto px-2 pb-2 md:flex-1 md:flex-col md:space-y-1 md:overflow-visible md:px-3 md:pb-0">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) =>
                `nav-link relative flex shrink-0 items-center gap-2 rounded-xl px-2.5 py-2 text-xs transition-all md:gap-3 md:px-3 md:py-2.5 md:text-sm ${
                isActive
                  ? "active text-white"
                  : "text-muted hover:text-white"
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full bg-accent" />
                )}
                <Icon size={17} />
                {label}
              </>
            )}
          </NavLink>
        ))}
      </nav>

      <div className="hidden border-t border-white/[0.08] px-5 py-4 md:block">
        <div className="mb-3">{refreshButton()}</div>
        <div className="flex items-center gap-2.5 rounded-xl border border-slate-400/15 bg-white/[0.02] p-2.5">
          <ShieldCheck size={15} className={`shrink-0 ${user.role === "admin" ? "text-accent" : "text-emerald-300"}`} aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-zinc-300">{user.username}</p>
            <p className="mt-0.5 text-[11px] capitalize text-zinc-500">{user.role} account</p>
          </div>
          <button type="button" onClick={() => void onSignOut()} aria-label="Sign out" title="Sign out" className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-zinc-400 hover:bg-white/[0.06] hover:text-white">
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
