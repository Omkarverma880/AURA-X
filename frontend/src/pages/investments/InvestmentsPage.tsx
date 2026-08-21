import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, TrendingUp, TrendingDown, Wallet, Target, PieChart as PieChartIcon } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/shared/StatCard";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { FinancialLock } from "@/components/shared/FinancialLock";
import { AddHoldingDialog } from "@/components/investments/AddHoldingDialog";
import { useHoldings, usePortfolioSummary } from "@/hooks/useInvestments";
import { isApiError } from "@/lib/api";
import { formatMoneyCompact, formatPercent } from "@/lib/format";
import { ASSET_TYPE_LABELS, ASSET_TYPE_COLORS } from "@/lib/investment-meta";

export function InvestmentsPage() {
  const [addOpen, setAddOpen] = useState(false);
  const { data: summary, isLoading: summaryLoading, error: summaryError } = usePortfolioSummary();
  const { data: holdings, isLoading: holdingsLoading } = useHoldings();

  if (isApiError(summaryError) && summaryError.status === 423) {
    return <FinancialLock title="Investments are confidential" description="Enter your Green PIN to view your portfolio." />;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Investments</h1>
          <p className="text-sm text-[var(--text-secondary)]">Your portfolio, at a glance.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/investments/goals">
            <Button variant="secondary"><Target className="h-4 w-4" /> Goal Planner</Button>
          </Link>
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add investment
          </Button>
        </div>
      </div>

      {summaryLoading ? (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Total Invested" icon={Wallet} value={<CurrencyDisplay value={summary?.total_invested} compact size="lg" />} />
          <StatCard label="Current Value" icon={TrendingUp} value={<CurrencyDisplay value={summary?.current_value} compact size="lg" />} />
          <StatCard
            label="Unrealised P/L"
            icon={summary && summary.unrealised_pnl >= 0 ? TrendingUp : TrendingDown}
            value={<CurrencyDisplay value={summary?.unrealised_pnl} compact size="lg" />}
            subtext={summary ? formatPercent(summary.return_percent, true) : undefined}
            trend={summary ? (summary.unrealised_pnl >= 0 ? "up" : "down") : undefined}
          />
          <StatCard
            label="XIRR"
            icon={PieChartIcon}
            value={summary?.xirr_percent !== null && summary?.xirr_percent !== undefined ? formatPercent(summary.xirr_percent) : "-"}
          />
        </div>
      )}

      {summary && summary.by_asset_type.length > 0 && (
        <Card className="grid grid-cols-1 gap-6 p-5 md:grid-cols-2">
          <div>
            <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Asset allocation</h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={summary.by_asset_type}
                    dataKey="current_value"
                    nameKey="asset_type"
                    innerRadius={55}
                    outerRadius={80}
                    paddingAngle={2}
                  >
                    {summary.by_asset_type.map((entry) => (
                      <Cell key={entry.asset_type} fill={ASSET_TYPE_COLORS[entry.asset_type] ?? "#8b5cf6"} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => formatMoneyCompact(Number(value))} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="flex flex-col justify-center gap-3">
            {summary.by_asset_type.map((entry) => (
              <div key={entry.asset_type} className="flex items-center gap-2.5">
                <span className="h-2.5 w-2.5 shrink-0 rounded-full" style={{ backgroundColor: ASSET_TYPE_COLORS[entry.asset_type] ?? "#8b5cf6" }} />
                <span className="flex-1 text-sm text-[var(--text-secondary)]">{ASSET_TYPE_LABELS[entry.asset_type] ?? entry.asset_type}</span>
                <span className="text-sm font-medium text-[var(--text-primary)]">{entry.share.toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Holdings</h2>
        {holdingsLoading ? (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 3 }, (_, i) => <SkeletonCard key={i} />)}
          </div>
        ) : !holdings?.length ? (
          <Card>
            <EmptyState
              icon={TrendingUp}
              title="Start building your investment picture"
              description="Add your first stock, fund, gold or FD to track it here."
              action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> Add Investment</Button>}
            />
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {holdings.map((holding) => (
              <Link key={holding.id} to={`/investments/${holding.id}`}>
                <Card className="h-full p-4 transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate font-semibold text-[var(--text-primary)]">{holding.name}</p>
                      <p className="text-xs text-[var(--text-tertiary)]">{ASSET_TYPE_LABELS[holding.asset_type] ?? holding.asset_type}</p>
                    </div>
                    <span
                      className={`shrink-0 text-xs font-semibold ${holding.return_percent >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}
                    >
                      {formatPercent(holding.return_percent, true)}
                    </span>
                  </div>
                  <div className="mt-3 flex items-end justify-between">
                    <CurrencyDisplay value={holding.current_value} compact size="lg" />
                    <span className="text-xs text-[var(--text-tertiary)]">invested {formatMoneyCompact(holding.invested_amount)}</span>
                  </div>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      <AddHoldingDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
