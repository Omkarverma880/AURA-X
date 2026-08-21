import { NavLink, Outlet } from "react-router-dom";
import { User, Shield, Palette, Tag, Bell, Database } from "lucide-react";
import { cn } from "@/lib/utils";

const TABS = [
  { to: "/settings/profile", label: "Account", icon: User },
  { to: "/settings/security", label: "Security", icon: Shield },
  { to: "/settings/appearance", label: "Appearance", icon: Palette },
  { to: "/settings/categories", label: "Categories", icon: Tag },
  { to: "/settings/notifications", label: "Notifications", icon: Bell },
  { to: "/settings/data", label: "Data", icon: Database },
];

export function SettingsLayout() {
  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-[var(--text-primary)]">Settings</h1>

      <div className="flex gap-1 overflow-x-auto rounded-xl bg-[var(--bg-inset)] p-1 text-sm no-scrollbar md:inline-flex">
        {TABS.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                "flex shrink-0 items-center gap-1.5 rounded-lg px-3.5 py-2 font-medium transition-colors",
                isActive ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-soft" : "text-[var(--text-tertiary)]",
              )
            }
          >
            <tab.icon className="h-4 w-4" /> {tab.label}
          </NavLink>
        ))}
      </div>

      <div className="max-w-2xl">
        <Outlet />
      </div>
    </div>
  );
}
