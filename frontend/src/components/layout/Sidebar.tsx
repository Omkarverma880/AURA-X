import { NavLink } from "react-router-dom";
import { BookOpenText } from "lucide-react";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";

export function Sidebar() {
  return (
    <aside className="hidden md:flex md:w-64 md:shrink-0 md:flex-col md:border-r md:border-[var(--border-subtle)] md:bg-[var(--bg-surface)]">
      <div className="flex h-16 items-center gap-2.5 px-6">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand)]">
          <BookOpenText className="h-5 w-5 text-white" strokeWidth={2} />
        </div>
        <div>
          <p className="text-sm font-bold leading-none text-[var(--text-primary)]">Aura X</p>
          <p className="mt-0.5 text-[10px] font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
            Money · Wealth · Goals · Life
          </p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-[var(--brand-soft)] text-[var(--brand-soft-text)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-inset)] hover:text-[var(--text-primary)]",
              )
            }
          >
            <item.icon className="h-[18px] w-[18px]" strokeWidth={2} />
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="px-6 py-4 text-[11px] text-[var(--text-tertiary)]">
        Your Money. Your Wealth. Your Goals. Your Life.
      </div>
    </aside>
  );
}
