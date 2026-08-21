import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lock, LockOpen, Menu, Search, Bell, LogOut, Settings as SettingsIcon, User } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { useFinancial, formatCountdown } from "@/contexts/FinancialContext";
import { Avatar } from "@/components/ui/Avatar";
import { Badge } from "@/components/ui/Badge";
import { cn } from "@/lib/utils";
import { SearchModal } from "@/components/shared/SearchModal";
import { MobileMenu } from "@/components/layout/MobileMenu";
import { useNotificationsUnreadCount } from "@/hooks/useNotifications";

export function Header() {
  const { user, logout } = useAuth();
  const { isUnlocked, isPinConfigured, secondsRemaining, promptUnlock, lock } = useFinancial();
  const [menuOpen, setMenuOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const { data: unreadCount } = useNotificationsUnreadCount();

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const handleLockClick = () => {
    if (isUnlocked) void lock();
    else promptUnlock();
  };

  return (
    <>
      <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]/90 px-4 backdrop-blur md:px-6">
        <button
          type="button"
          className="rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-inset)] md:hidden"
          onClick={() => setMobileNavOpen(true)}
          aria-label="Open menu"
        >
          <Menu className="h-5 w-5" />
        </button>

        <Link to="/dashboard" className="flex items-center gap-2 md:hidden">
          <span className="text-sm font-bold text-[var(--text-primary)]">Aura X</span>
        </Link>

        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="ml-auto flex h-9 flex-1 max-w-xs items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--bg-inset)] px-3 text-sm text-[var(--text-tertiary)] hover:border-[var(--brand)] md:ml-0 md:mr-auto"
        >
          <Search className="h-4 w-4" />
          <span className="hidden sm:inline">Search everything...</span>
        </button>

        {/* Financial lock indicator */}
        <button
          type="button"
          onClick={handleLockClick}
          className={cn(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors",
            isUnlocked
              ? "border-[var(--positive)]/30 bg-[var(--positive-soft)] text-[var(--positive-soft-text)]"
              : "border-[var(--border-default)] bg-[var(--bg-inset)] text-[var(--text-secondary)]",
          )}
          title={isUnlocked ? "Lock financial data" : "Unlock financial data"}
        >
          {isUnlocked ? <LockOpen className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
          <span className="hidden sm:inline">
            {!isPinConfigured
              ? "Set up Green PIN"
              : isUnlocked
                ? formatCountdown(secondsRemaining)
                : "Locked"}
          </span>
        </button>

        <Link
          to="/settings/notifications"
          className="relative rounded-lg p-2 text-[var(--text-secondary)] hover:bg-[var(--bg-inset)]"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {!!unreadCount && unreadCount > 0 && (
            <Badge
              variant="negative"
              className="absolute -right-0.5 -top-0.5 h-4 min-w-4 justify-center rounded-full px-1 text-[10px]"
            >
              {unreadCount > 9 ? "9+" : unreadCount}
            </Badge>
          )}
        </Link>

        <div className="relative" ref={menuRef}>
          <button type="button" onClick={() => setMenuOpen((v) => !v)} className="block">
            <Avatar name={user?.full_name ?? "?"} src={user?.profile?.avatar_url} size="sm" />
          </button>

          {menuOpen && (
            <div
              className="absolute right-0 top-11 w-56 rounded-xl border border-[var(--border-subtle)] bg-[var(--bg-surface)] p-1.5 animate-slide-up"
              style={{ boxShadow: "var(--shadow-elevated)" }}
            >
              <div className="px-3 py-2">
                <p className="truncate text-sm font-medium text-[var(--text-primary)]">{user?.full_name}</p>
                <p className="truncate text-xs text-[var(--text-tertiary)]">{user?.email}</p>
              </div>
              <div className="my-1 h-px bg-[var(--border-subtle)]" />
              <MenuLink icon={User} label="Profile" onClick={() => { setMenuOpen(false); navigate("/settings/profile"); }} />
              <MenuLink icon={SettingsIcon} label="Settings" onClick={() => { setMenuOpen(false); navigate("/settings"); }} />
              <MenuLink
                icon={LogOut}
                label="Sign out"
                onClick={() => {
                  setMenuOpen(false);
                  void logout().then(() => navigate("/login"));
                }}
              />
            </div>
          )}
        </div>
      </header>

      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} />
      <MobileMenu open={mobileNavOpen} onClose={() => setMobileNavOpen(false)} />
    </>
  );
}

function MenuLink({ icon: Icon, label, onClick }: { icon: typeof User; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-inset)] hover:text-[var(--text-primary)]"
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}
