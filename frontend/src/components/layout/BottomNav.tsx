import { NavLink } from "react-router-dom";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";

export function BottomNav() {
  const items = NAV_ITEMS.filter((item) => item.mobile);

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex border-t border-[var(--border-subtle)] bg-[var(--bg-surface)]/95 backdrop-blur md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          className={({ isActive }) =>
            cn(
              "flex flex-1 flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
              isActive ? "text-[var(--brand)]" : "text-[var(--text-tertiary)]",
            )
          }
        >
          {({ isActive }) => (
            <>
              <item.icon className="h-5 w-5" strokeWidth={isActive ? 2.25 : 2} />
              {item.label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}
