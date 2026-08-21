import { useState } from "react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { FinancialLock } from "@/components/shared/FinancialLock";
import { useAnalyticsOverview } from "@/hooks/useDashboard";
import { useLedgerAnalytics } from "@/hooks/useBahiKhata";
import { formatMoneyCompact } from "@/lib/format";
import { cn } from "@/lib/utils";

type Tab = "financial" | "bahi-khata" | "investments" | "life";

const TABS: { key: Tab; label: string }[] = [
  { key: "financial", label: "Financial" },
  { key: "bahi-khata", label: "Bahi Khata" },
  { key: "investments", label: "Investments" },
  { key: "life", label: "Life" },
];

export function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>("financial");
  const { data: overview, isLoading } = useAnalyticsOverview();
  const { data: ledgerAnalytics } = useLedgerAnalytics();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--text-primary)]">Analytics</h1>
        <p className="text-sm text-[var(--text-secondary)]">The complete picture, across every module.</p>
      </div>

      <div className="flex gap-1 overflow-x-auto rounded-xl bg-[var(--bg-inset)] p-1 text-sm no-scrollbar">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              "shrink-0 rounded-lg px-4 py-2 font-medium transition-colors",
              tab === t.key ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-soft" : "text-[var(--text-tertiary)]",
            )}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <>
          {tab === "financial" && (
            overview?.financial_locked ? (
              <FinancialLock title="Financial analytics are confidential" />
            ) : (
              <FinancialTab summary={overview?.financial ?? null} />
            )
          )}
          {tab === "bahi-khata" && <BahiKhataTab analytics={ledgerAnalytics ?? null} />}
          {tab === "investments" && (
            overview?.financial_locked ? (
              <FinancialLock title="Investment analytics are confidential" />
            ) : (
              <InvestmentsTab summary={overview?.investments ?? null} />
            )
          )}
          {tab === "life" && <LifeTab life={overview?.life ?? null} />}
        </>
      )}
    </div>
  );
}

function FinancialTab({ summary }: { summary: import("@/types").MonthlySummary | null }) {
  if (!summary) return null;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Income" value={summary.income} />
        <MetricCard label="Expenses" value={summary.expenses} />
        <MetricCard label="Savings" value={summary.savings} />
        <MetricCard label="Savings Rate" value={`${summary.savings_rate.toFixed(0)}%`} isText />
      </div>
      {summary.by_category.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">Expense by category</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={summary.by_category} layout="vertical" margin={{ left: 8 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" horizontal={false} />
                <XAxis type="number" tickFormatter={(v) => formatMoneyCompact(v)} tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11, fill: "var(--text-secondary)" }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v) => formatMoneyCompact(Number(v))} />
                <Bar dataKey="amount" fill="var(--brand)" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}
    </div>
  );
}

function BahiKhataTab({ analytics }: { analytics: import("@/types").LedgerAnalytics | null }) {
  if (!analytics) return null;
  const { summary, monthly_trend, outstanding_by_person } = analytics;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Total Given" value={summary.total_given} />
        <MetricCard label="Outstanding Receivable" value={summary.outstanding_receivable} />
        <MetricCard label="Total Borrowed" value={summary.total_borrowed} />
        <MetricCard label="Settlement Rate" value={`${summary.settlement_rate.toFixed(0)}%`} isText />
      </div>

      {monthly_trend.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">Given vs received</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={monthly_trend}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
                <YAxis tickFormatter={(v) => formatMoneyCompact(v)} tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} width={56} />
                <Tooltip formatter={(v) => formatMoneyCompact(Number(v))} />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="given" name="Given" stroke="var(--positive)" fill="var(--positive-soft)" strokeWidth={2} />
                <Area type="monotone" dataKey="received" name="Received" stroke="var(--info)" fill="var(--info-soft)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      {outstanding_by_person.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Outstanding by person</h2>
          <div className="space-y-2">
            {outstanding_by_person.map((p) => (
              <div key={p.person_id} className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-secondary)]">{p.name}</span>
                <CurrencyDisplay value={p.total} compact clickToUnlock={false} />
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function InvestmentsTab({ summary }: { summary: import("@/types").PortfolioSummary | null }) {
  if (!summary) return null;
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <MetricCard label="Invested" value={summary.total_invested} />
      <MetricCard label="Current Value" value={summary.current_value} />
      <MetricCard label="Total Return" value={summary.total_return} />
      <MetricCard label="XIRR" value={summary.xirr_percent !== null ? `${summary.xirr_percent.toFixed(1)}%` : "-"} isText />
    </div>
  );
}

function LifeTab({ life }: { life: import("@/types").LifeAnalytics | null }) {
  if (!life) return null;
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <MetricCard label="Goals Completed" value={String(life.goals_completed)} isText />
        <MetricCard label="In Progress" value={String(life.goals_in_progress)} isText />
        <MetricCard label="Trips Completed" value={String(life.trips_completed)} isText />
        <MetricCard label="Memory Albums" value={String(life.memory_count)} isText />
      </div>
      {life.trackers.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Trackers</h2>
          <div className="space-y-3">
            {life.trackers.map((t) => (
              <div key={t.id} className="flex items-center justify-between text-sm">
                <span className="text-[var(--text-secondary)]">{t.title}</span>
                <Badge variant="brand">{t.completed}/{t.total}</Badge>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
}

function MetricCard({ label, value, isText }: { label: string; value: number | string; isText?: boolean }) {
  return (
    <Card className="p-4">
      <p className="text-xs font-medium text-[var(--text-secondary)]">{label}</p>
      {isText ? (
        <p className="mt-1.5 text-xl font-bold text-[var(--text-primary)]">{value}</p>
      ) : (
        <CurrencyDisplay value={value as number} compact size="lg" className="mt-1.5 block" />
      )}
    </Card>
  );
}
