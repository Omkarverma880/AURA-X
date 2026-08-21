import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, Receipt, PiggyBank, TrendingDown, TrendingUp, Wallet2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/shared/StatCard";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { CategoryIcon } from "@/components/shared/CategoryIcon";
import { MonthPicker, currentPeriod } from "@/components/shared/MonthPicker";
import { AddExpenseDialog } from "@/components/expenses/AddExpenseDialog";
import { useExpenses, useMonthlySummary } from "@/hooks/useExpenses";
import { formatDate, formatPercent } from "@/lib/format";
import { isApiError } from "@/lib/api";

export function ExpensesPage() {
  const [period, setPeriod] = useState(currentPeriod());
  const [search, setSearch] = useState("");
  const [addOpen, setAddOpen] = useState(false);

  const { data: summary, error: summaryError } = useMonthlySummary(period);
  const { data: expenses, isLoading } = useExpenses({ period, search: search || undefined, sort: "recent", page_size: 50 });

  const locked = isApiError(summaryError) && summaryError.status === 423;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Expenses</h1>
          <p className="text-sm text-[var(--text-secondary)]">Where your money goes.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <MonthPicker value={period} onChange={setPeriod} />
          <Link to="/expenses/income">
            <Button variant="secondary">Income</Button>
          </Link>
          <Link to="/expenses/budgets">
            <Button variant="secondary">Budgets</Button>
          </Link>
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add expense
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Income"
          icon={TrendingUp}
          value={<CurrencyDisplay value={locked ? null : summary?.income} compact size="lg" />}
        />
        <StatCard
          label="Expenses"
          icon={TrendingDown}
          value={<CurrencyDisplay value={locked ? null : summary?.expenses} compact size="lg" />}
          subtext={summary && !locked ? `${formatPercent(summary.change_percent, true)} vs last month` : undefined}
        />
        <StatCard
          label="Savings"
          icon={PiggyBank}
          value={<CurrencyDisplay value={locked ? null : summary?.savings} compact size="lg" />}
          subtext={summary && !locked ? `${summary.savings_rate.toFixed(0)}% savings rate` : undefined}
        />
        <StatCard
          label="Daily average"
          icon={Wallet2}
          value={<CurrencyDisplay value={locked ? null : summary?.daily_average} compact size="lg" />}
        />
      </div>

      {summary && !locked && summary.by_category.length > 0 && (
        <Card className="p-5">
          <h2 className="mb-4 text-sm font-semibold text-[var(--text-primary)]">By category</h2>
          <div className="space-y-3">
            {summary.by_category.slice(0, 6).map((cat) => (
              <div key={cat.category_id ?? cat.name} className="flex items-center gap-3">
                <div
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                  style={{ backgroundColor: `${cat.color ?? "#94a3b8"}22` }}
                >
                  <CategoryIcon icon={cat.icon} color={cat.color} className="h-4 w-4" />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="truncate font-medium text-[var(--text-primary)]">{cat.name}</span>
                    <CurrencyDisplay value={cat.amount} compact clickToUnlock={false} size="sm" />
                  </div>
                  <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-[var(--bg-inset)]">
                    <div
                      className="h-full rounded-full"
                      style={{ width: `${cat.share}%`, backgroundColor: cat.color ?? "var(--brand)" }}
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      <div className="relative max-w-xs">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
        <Input placeholder="Search expenses..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {isLoading ? (
        <Card><SkeletonList rows={6} /></Card>
      ) : !expenses?.items.length ? (
        <Card>
          <EmptyState
            icon={Receipt}
            title="Start tracking where your money goes"
            description="Add your first expense to see it here."
            action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> Add Expense</Button>}
          />
        </Card>
      ) : (
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {expenses.items.map((expense) => (
            <div key={expense.id} className="flex items-center gap-3 p-4">
              <div
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl"
                style={{ backgroundColor: `${expense.category_color ?? "#94a3b8"}22` }}
              >
                <CategoryIcon icon={expense.category_icon} color={expense.category_color} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                  {expense.description || expense.merchant || expense.category_name || "Expense"}
                </p>
                <p className="truncate text-xs text-[var(--text-tertiary)]">
                  {formatDate(expense.spent_on, "short")}
                  {expense.category_name ? ` · ${expense.category_name}` : ""}
                  {expense.merchant && expense.description ? ` · ${expense.merchant}` : ""}
                </p>
              </div>
              <CurrencyDisplay value={expense.amount} clickToUnlock={false} />
            </div>
          ))}
        </Card>
      )}

      <AddExpenseDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
