import { NavLink } from "react-router-dom";

import { AuraSigil } from "@/components/aura/AuraSigil";
import { Avatar } from "@/components/ui/Avatar";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

/**
 * Primary navigation.
 *
 * Restyled only - NAV_ITEMS remains the single source of truth for what
 * exists and where it goes, so nothing here can drift from the router. The
 * two groups below are a presentational split of that same list: the six
 * dimensions of the universe, then the tools that observe them.
 *
 * Stays theme-aware on purpose. Home and the landing page are deliberately
 * always dark, but this chrome is shared with every module, and those still
 * follow the user's light/dark preference.
 */
const SYSTEM_ROUTES = new Set(["/analytics", "/settings"]);

export function Sidebar() {
  const { user } = useAuth();

  const dimensions = NAV_ITEMS.filter((item) => !SYSTEM_ROUTES.has(item.to));
  const system = NAV_ITEMS.filter((item) => SYSTEM_ROUTES.has(item.to));

  return (
    <aside className="hidden md:flex md:w-64 md:shrink-0 md:flex-col md:border-r md:border-[var(--border-subtle)] md:bg-[var(--bg-surface)]">
      <div className="flex h-16 items-center gap-3 px-6">
        <AuraSigil size={30} />
        <div>
          <p className="text-sm font-light tracking-[0.18em] text-[var(--text-primary)]">
            AURA <span className="font-semibold text-[var(--brand)]">X</span>
          </p>
          <p className="mt-0.5 text-[9px] font-medium uppercase tracking-[0.16em] text-[var(--text-tertiary)]">
            Money · Wealth · Goals · Life
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {dimensions.map((item) => (
          <SidebarLink key={item.to} to={item.to} label={item.label} icon={item.icon} />
        ))}

        <div className="!my-3 h-px bg-[var(--border-subtle)]" />

        {system.map((item) => (
          <SidebarLink key={item.to} to={item.to} label={item.label} icon={item.icon} />
        ))}
      </nav>

      <NavLink
        to="/settings/profile"
        className="flex items-center gap-3 border-t border-[var(--border-subtle)] px-4 py-3.5 transition-colors hover:bg-[var(--bg-inset)]"
      >
        <Avatar name={user?.full_name ?? "?"} src={user?.profile?.avatar_url} size="sm" />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-[var(--text-primary)]">
            {user?.full_name}
          </p>
          <p className="truncate text-[11px] text-[var(--text-tertiary)]">
            {user?.username ? `@${user.username}` : user?.email}
          </p>
        </div>
      </NavLink>
    </aside>
  );
}

function SidebarLink({
  to,
  label,
  icon: Icon,
}: {
  to: string;
  label: string;
  icon: (typeof NAV_ITEMS)[number]["icon"];
}) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        cn(
          "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors duration-300",
          isActive
            ? "bg-[var(--brand-soft)] text-[var(--brand-soft-text)]"
            : "text-[var(--text-secondary)] hover:bg-[var(--bg-inset)] hover:text-[var(--text-primary)]",
        )
      }
    >
      {({ isActive }) => (
        <>
          {/* A thin gold marker on the active route - the same accent that
              lights the orb, at its smallest. */}
          <span
            className={cn(
              "absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-[var(--brand)] transition-opacity duration-300",
              isActive ? "opacity-100" : "opacity-0",
            )}
          />
          <Icon className="h-[18px] w-[18px]" strokeWidth={1.8} />
          {label}
        </>
      )}
    </NavLink>
  );
}
