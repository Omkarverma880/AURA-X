import {
  ComposedChart, Bar, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { Lock, LineChart } from "lucide-react";

import { formatMoneyCompact } from "@/lib/format";

function monthLabel(month: string): string {
  const [year, m] = month.split("-");
  return new Date(Number(year), Number(m) - 1, 1).toLocaleDateString("en-US", { month: "short" });
}

function SectionHeading({
  children,
  icon: Icon,
}: {
  children: React.ReactNode;
  icon?: typeof LineChart;
}) {
  return (
    <h2 className="mb-4 flex items-center gap-2 text-[10px] uppercase tracking-[0.24em] text-[var(--aura-text-faint)]">
      {Icon && <Icon className="h-3.5 w-3.5" strokeWidth={1.6} />}
      {children}
      <span className="ml-1 h-px flex-1 bg-[var(--aura-line)]" />
    </h2>
  );
}

/**
 * Month-on-month income, spend and savings.
 *
 * Stays locked behind the Green PIN exactly as before - the trend query is
 * only enabled while unlocked, so a locked session never even requests the
 * figures.
 */
export default function TrendPanel({
  trend,
  isUnlocked,
  onUnlock,
}: {
  trend: Array<{ month: string; income: number; expenses: number; savings: number }> | undefined;
  isUnlocked: boolean;
  onUnlock: () => void;
}) {
  return (
    <section>
      <SectionHeading icon={LineChart}>Cash flow, month on month</SectionHeading>

      {!isUnlocked ? (
        <div className="aura-panel flex flex-wrap items-center justify-between gap-4 p-6">
          <div className="flex items-center gap-3.5">
            <span className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl border border-[var(--aura-line-strong)] bg-[rgba(232,168,60,0.06)]">
              <Lock className="h-5 w-5 text-[var(--aura-gold)]" strokeWidth={1.6} />
            </span>
            <div>
              <p className="text-sm text-[var(--aura-text)]">This trend is confidential</p>
              <p className="text-xs text-[var(--aura-text-faint)]">
                Enter your Green PIN to reveal income and spending.
              </p>
            </div>
          </div>
          <button
            onClick={onUnlock}
            className="rounded-full border border-[var(--aura-line-strong)] px-5 py-2 text-xs uppercase tracking-[0.16em] text-[var(--aura-gold)] transition-colors duration-500 hover:bg-[rgba(232,168,60,0.1)]"
          >
            Unlock
          </button>
        </div>
      ) : trend && trend.length > 0 ? (
        <div className="aura-panel p-5 sm:p-6">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={trend} margin={{ left: -12 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                <XAxis
                  dataKey="month"
                  tickFormatter={monthLabel}
                  tick={{ fontSize: 11, fill: "rgba(242,242,245,0.38)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  tickFormatter={(v) => formatMoneyCompact(v)}
                  tick={{ fontSize: 11, fill: "rgba(242,242,245,0.38)" }}
                  axisLine={false}
                  tickLine={false}
                  width={56}
                />
                <Tooltip
                  cursor={{ fill: "rgba(255,255,255,0.03)" }}
                  contentStyle={{
                    background: "#0b0b12",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                    fontSize: 12,
                  }}
                  labelStyle={{ color: "rgba(242,242,245,0.62)" }}
                  formatter={(value, name) => [formatMoneyCompact(Number(value)), name]}
                  labelFormatter={(label) => monthLabel(String(label))}
                />
                <Legend wrapperStyle={{ fontSize: 12, color: "rgba(242,242,245,0.62)" }} />
                <Bar dataKey="income" name="Income" fill="#4ade80" radius={[4, 4, 0, 0]} maxBarSize={26} />
                <Bar dataKey="expenses" name="Expenses" fill="#f87171" radius={[4, 4, 0, 0]} maxBarSize={26} />
                <Line
                  type="monotone"
                  dataKey="savings"
                  name="Savings"
                  stroke="#e8a83c"
                  strokeWidth={2.5}
                  dot={{ r: 3, fill: "#e8a83c", strokeWidth: 0 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      ) : (
        <div className="aura-panel flex flex-col items-center gap-2 px-6 py-12 text-center">
          <LineChart className="h-5 w-5 text-[var(--aura-text-faint)]" strokeWidth={1.5} />
          <p className="text-sm text-[var(--aura-text-dim)]">Not enough history yet</p>
          <p className="text-xs text-[var(--aura-text-faint)]">
            Log a month of income and expenses to see the trend.
          </p>
        </div>
      )}
    </section>
  );
}

