import { lazy, Suspense } from "react";
import { Link } from "react-router-dom";
import { Bell, Clock, Sparkles } from "lucide-react";

import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { Skeleton } from "@/components/ui/Skeleton";
import { CommandHeader } from "@/components/dashboard/CommandHeader";
import { OverviewGrid } from "@/components/dashboard/OverviewGrid";
import { DimensionTiles } from "@/components/dashboard/DimensionTiles";
import { useAuraReveal } from "@/components/aura/useAuraReveal";
import { useDashboard } from "@/hooks/useDashboard";
import { useExpenseTrend } from "@/hooks/useExpenses";
import { useAuth } from "@/contexts/AuthContext";
import { useFinancial } from "@/contexts/FinancialContext";
import { formatDate, formatRelativeTime } from "@/lib/format";

/**
 * recharts is ~300KB and only the cash-flow panel needs it. Loading it with
 * the dashboard delayed first paint noticeably after sign-in; split out, the
 * command centre renders immediately and the chart arrives behind it.
 */
const TrendPanel = lazy(() => import("@/components/dashboard/TrendPanel"));

/**
 * The Aura X command centre.
 *
 * Deliberately always dark, whatever the user's light/dark preference: this
 * page and the public landing page are one continuous universe, and every
 * other module still follows the theme normally.
 *
 * Data and privacy behaviour are unchanged from the previous dashboard - the
 * same useDashboard/useExpenseTrend hooks, the same CurrencyDisplay masking,
 * the same server-side Green PIN gate. Only the surface is new.
 */
export function DashboardPage() {
  const { user } = useAuth();
  const { data, isLoading } = useDashboard();
  const { isUnlocked, promptUnlock } = useFinancial();
  const { data: trend } = useExpenseTrend(6, isUnlocked);
  // Re-scan once the dashboard data arrives: the revealed content does not
  // exist while the skeleton is on screen.
  const revealRef = useAuraReveal<HTMLDivElement>([data]);

  return (
    // Full-bleed: cancels AppShell's main padding (px-4 pb-24 pt-5 /
    // md:px-8 md:pb-8 md:pt-5) so the universe reaches the edges of the
    // content area instead of floating in a themed frame. If that padding
    // ever changes, these offsets must change with it.
    <div className="aura-surface aura-ambient relative -mx-4 -mb-24 -mt-5 min-h-dvh overflow-hidden md:-mx-8 md:-mb-8">
      {isLoading || !data ? (
        <DashboardSkeleton />
      ) : (
        <div ref={revealRef}>
          <CommandHeader greeting={data.greeting} fallbackName={user?.full_name} />

          <div className="space-y-9 px-5 pb-16 md:px-10">
            <OverviewGrid snapshot={data.snapshot} />

            {data.snapshot.net_savings !== null && (
              // Savings is an analytics figure, so the card opens Analytics.
              <Link
                to="/analytics"
                className="aura-panel aura-panel-interactive aura-glow flex flex-wrap items-center justify-between gap-4 p-5 sm:p-6"
              >
                <div>
                  <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--aura-text-faint)]">
                    Net savings this month
                  </p>
                  <div className="mt-2 text-[var(--aura-text)]">
                    <CurrencyDisplay value={data.snapshot.net_savings} size="xl" />
                  </div>
                </div>
                {data.snapshot.savings_rate !== null && (
                  <span
                    className="rounded-full border px-4 py-1.5 text-xs tracking-wide"
                    style={{
                      borderColor:
                        data.snapshot.savings_rate >= 20
                          ? "rgba(74,222,128,0.3)"
                          : "rgba(251,191,36,0.3)",
                      color: data.snapshot.savings_rate >= 20 ? "#86efac" : "#fcd34d",
                    }}
                  >
                    {data.snapshot.savings_rate.toFixed(0)}% savings rate
                  </span>
                )}
              </Link>
            )}

            <Suspense fallback={<div className="aura-panel h-56 animate-pulse" />}>
              <TrendPanel trend={trend} isUnlocked={isUnlocked} onUnlock={promptUnlock} />
            </Suspense>

            <section>
              <SectionHeading>Your dimensions</SectionHeading>
              <DimensionTiles cards={data.cards} />
            </section>

            <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
              <section>
                <SectionHeading icon={Bell}>Upcoming</SectionHeading>
                <div className="aura-panel divide-y divide-[var(--aura-line)] overflow-hidden">
                  {data.upcoming_reminders.length === 0 ? (
                    <EmptyRow icon={Sparkles} title="Nothing due soon" detail="You're all caught up." />
                  ) : (
                    data.upcoming_reminders.map((reminder, i) => (
                      <div key={i} className="flex items-center gap-3 p-4">
                        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-[rgba(251,191,36,0.25)] bg-[rgba(251,191,36,0.06)]">
                          <Clock className="h-4 w-4 text-[#fcd34d]" strokeWidth={1.6} />
                        </span>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm text-[var(--aura-text)]">{reminder.title}</p>
                          <p className="truncate text-xs text-[var(--aura-text-faint)]">{reminder.detail}</p>
                        </div>
                        <span className="shrink-0 text-xs text-[var(--aura-text-faint)]">
                          {formatDate(reminder.due_date, "short")}
                        </span>
                      </div>
                    ))
                  )}
                </div>
              </section>

              <section>
                <SectionHeading>Recent activity</SectionHeading>
                <div className="aura-panel divide-y divide-[var(--aura-line)] overflow-hidden">
                  {data.recent_activity.length === 0 ? (
                    <EmptyRow icon={Sparkles} title="No activity yet" detail="Your actions will show up here." />
                  ) : (
                    data.recent_activity.map((item, i) => (
                      <div key={i} className="p-4">
                        <p className="truncate text-sm text-[var(--aura-text-dim)]">
                          {item.summary ?? item.action}
                        </p>
                        <p className="mt-0.5 text-xs text-[var(--aura-text-faint)]">
                          {formatRelativeTime(item.created_at)}
                        </p>
                      </div>
                    ))
                  )}
                </div>
              </section>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SectionHeading({
  children,
  icon: Icon,
}: {
  children: React.ReactNode;
  icon?: typeof Bell;
}) {
  return (
    <h2 className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[var(--aura-text-faint)]">
      {Icon && <Icon className="h-3.5 w-3.5" strokeWidth={1.6} />}
      {children}
      <span className="ml-1 h-px flex-1 bg-[var(--aura-line)]" />
    </h2>
  );
}

function EmptyRow({
  icon: Icon,
  title,
  detail,
}: {
  icon: typeof Sparkles;
  title: string;
  detail: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2 px-6 py-12 text-center">
      <Icon className="h-5 w-5 text-[var(--aura-text-faint)]" strokeWidth={1.5} />
      <p className="text-sm text-[var(--aura-text-dim)]">{title}</p>
      <p className="text-xs text-[var(--aura-text-faint)]">{detail}</p>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-8 px-5 py-10 md:px-10">
      <Skeleton className="h-10 w-72 bg-white/5" />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {Array.from({ length: 4 }, (_, i) => (
          <Skeleton key={i} className="h-28 bg-white/5" />
        ))}
      </div>
      <Skeleton className="h-72 bg-white/5" />
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: 6 }, (_, i) => (
          <Skeleton key={i} className="h-44 bg-white/5" />
        ))}
      </div>
    </div>
  );
}
