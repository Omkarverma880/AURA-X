import { NavLink } from "react-router-dom";
import { BookOpenText } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { NAV_ITEMS } from "@/components/layout/nav-items";
import { cn } from "@/lib/utils";

export function MobileMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  return (
    <Dialog open={open} onClose={onClose}>
      <div className="-mt-2 mb-4 flex items-center gap-2.5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand)]">
          <BookOpenText className="h-5 w-5 text-white" />
        </div>
        <span className="text-sm font-bold text-[var(--text-primary)]">Aura X</span>
      </div>
      <nav className="space-y-1">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            onClick={onClose}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-xl px-3 py-3 text-sm font-medium",
                isActive
                  ? "bg-[var(--brand-soft)] text-[var(--brand-soft-text)]"
                  : "text-[var(--text-secondary)] hover:bg-[var(--bg-inset)]",
              )
            }
          >
            <item.icon className="h-5 w-5" />
            {item.label}
          </NavLink>
        ))}
      </nav>
    </Dialog>
  );
}
