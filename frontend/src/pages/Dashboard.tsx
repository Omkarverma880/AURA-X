import { Link } from "react-router-dom";
import {
  HandCoins,
  Wallet,
  Receipt,
  TrendingUp,
  Target,
  Images,
  ArrowUpRight,
  ArrowDownRight,
  Bell,
  Clock,
  Sparkles,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton, SkeletonCard } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatCard } from "@/components/shared/StatCard";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { useDashboard } from "@/hooks/useDashboard";
import { useAuth } from "@/contexts/AuthContext";
import { formatDate, formatRelativeTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ModuleCard } from "@/types";
import type { LucideIcon } from "lucide-react";

const MODULE_META: Record<string, { icon: LucideIcon; route: string; label: string }> = {
  bahi_khata: { icon: HandCoins, route: "/bahi-khata", label: "Bahi Khata" },
  expenses: { icon: Receipt, route: "/expenses", label: "Expenses" },
  investments: { icon: TrendingUp, route: "/investments", label: "Investments" },
  goals: { icon: Target, route: "/goals", label: "Goals" },
  life: { icon: Images, route: "/memories", label: "Life & Memories" },
};

export function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useDashboard();

  if (isLoading || !data) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 5 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      </div>
    );
  }

  const { greeting, snapshot, cards, upcoming_reminders, recent_activity } = data;

  return (
    <div className="space-y-7">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">
          {greeting.greeting}, {greeting.name || user?.full_name?.split(" ")[0]}
        </h1>
        <p className="text-sm text-[var(--text-secondary)]">{formatDate(greeting.date, "long")}</p>
      </div>

      {/* Financial snapshot */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="To Receive"
          icon={HandCoins}
          value={<CurrencyDisplay value={snapshot.to_receive} compact clickToUnlock={false} size="lg" />}
        />
        <StatCard
          label="To Pay"
          icon={Wallet}
          value={<CurrencyDisplay value={snapshot.to_pay} compact clickToUnlock={false} size="lg" />}
        />
        <StatCard
          label="Monthly Income"
          icon={ArrowUpRight}
          value={<CurrencyDisplay value={snapshot.monthly_income} compact size="lg" />}
        />
        <StatCard
          label="Monthly Expenses"
          icon={ArrowDownRight}
          value={<CurrencyDisplay value={snapshot.monthly_expenses} compact size="lg" />}
        />
      </div>

      {snapshot.net_savings !== null && (
        <Card className="flex flex-wrap items-center justify-between gap-3 p-5">
          <div>
            <p className="text-sm text-[var(--text-secondary)]">Net savings this month</p>
            <CurrencyDisplay value={snapshot.net_savings} size="xl" />
          </div>
          {snapshot.savings_rate !== null && (
            <Badge variant={snapshot.savings_rate >= 20 ? "positive" : "warning"}>
              {snapshot.savings_rate.toFixed(0)}% savings rate
            </Badge>
          )}
        </Card>
      )}

      {/* Module cards */}
      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Your world at a glance</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {cards.map((card) => (
            <ModuleCardTile key={card.module} card={card} />
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        {/* Reminders */}
        <div>
          <h2 className="mb-3 flex items-center gap-1.5 text-sm font-semibold text-[var(--text-primary)]">
            <Bell className="h-4 w-4" /> Upcoming reminders
          </h2>
          <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
            {upcoming_reminders.length === 0 ? (
              <EmptyState icon={Sparkles} title="Nothing due soon" description="You're all caught up." />
            ) : (
              upcoming_reminders.map((reminder, i) => (
                <div key={i} className="flex items-center gap-3 p-4">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-[var(--warning-soft)]">
                    <Clock className="h-4 w-4 text-[var(--warning)]" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[var(--text-primary)]">{reminder.title}</p>
                    <p className="truncate text-xs text-[var(--text-tertiary)]">{reminder.detail}</p>
                  </div>
                  <span className="shrink-0 text-xs text-[var(--text-tertiary)]">{formatDate(reminder.due_date, "short")}</span>
                </div>
              ))
            )}
          </Card>
        </div>

        {/* Recent activity */}
        <div>
          <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Recent activity</h2>
          <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
            {recent_activity.length === 0 ? (
              <EmptyState icon={Sparkles} title="No activity yet" description="Your recent actions will show up here." />
            ) : (
              recent_activity.map((item, i) => (
                <div key={i} className="flex items-center gap-3 p-4">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-[var(--text-primary)]">{item.summary ?? item.action}</p>
                    <p className="text-xs text-[var(--text-tertiary)]">{formatRelativeTime(item.created_at)}</p>
                  </div>
                </div>
              ))
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}

function ModuleCardTile({ card }: { card: ModuleCard }) {
  const meta = MODULE_META[card.module];
  const Icon = meta?.icon ?? Target;

  return (
    <Link to={meta?.route ?? "/dashboard"}>
      <Card className="flex h-full items-center gap-4 p-5 transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
          <Icon className="h-6 w-6 text-[var(--brand)]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">
            {meta?.label ?? card.module}
          </p>
          <p
            className={cn(
              "mt-0.5 truncate text-base font-semibold",
              card.locked ? "tracking-[0.2em] text-[var(--text-tertiary)]" : "text-[var(--text-primary)]",
            )}
          >
            {card.headline}
          </p>
          <p className="truncate text-xs text-[var(--text-tertiary)]">{card.subtext}</p>
        </div>
      </Card>
    </Link>
  );
}
