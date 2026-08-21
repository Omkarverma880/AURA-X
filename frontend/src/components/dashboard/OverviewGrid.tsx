import { HandCoins, Wallet, ArrowUpRight, ArrowDownRight, type LucideIcon } from "lucide-react";

import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import type { FinancialSnapshot } from "@/types";

/**
 * The four figures that open the command centre.
 *
 * Every value comes from GET /dashboard - nothing is derived on the client and
 * nothing is invented. Where the brief asked for "Net Worth" and "Available
 * Balance", the API has no such fields, so this shows what genuinely exists
 * (receivable, payable, income, expenses) rather than a fabricated number.
 *
 * Masking is entirely CurrencyDisplay's job: the server sends `null` for
 * anything the Green PIN is guarding, and a null renders as ₹ ••••••.
 */
export function OverviewGrid({ snapshot }: { snapshot: FinancialSnapshot }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <OverviewTile
        label="People owe you"
        icon={HandCoins}
        accent="positive"
        value={<CurrencyDisplay value={snapshot.to_receive} compact clickToUnlock={false} size="lg" />}
        footnote={snapshot.money_given > 0 ? "Outstanding receivable" : "Nothing lent yet"}
      />
      <OverviewTile
        label="You owe"
        icon={Wallet}
        accent="negative"
        value={<CurrencyDisplay value={snapshot.to_pay} compact clickToUnlock={false} size="lg" />}
        footnote={snapshot.money_borrowed > 0 ? "Outstanding payable" : "Nothing borrowed"}
      />
      <OverviewTile
        label="Monthly income"
        icon={ArrowUpRight}
        accent="positive"
        value={<CurrencyDisplay value={snapshot.monthly_income} compact size="lg" />}
        footnote="This month"
      />
      <OverviewTile
        label="Monthly spend"
        icon={ArrowDownRight}
        accent="negative"
        value={<CurrencyDisplay value={snapshot.monthly_expenses} compact size="lg" />}
        footnote="This month"
      />
    </div>
  );
}

function OverviewTile({
  label,
  icon: Icon,
  value,
  footnote,
  accent,
}: {
  label: string;
  icon: LucideIcon;
  value: React.ReactNode;
  footnote: string;
  accent: "positive" | "negative";
}) {
  return (
    <div className="aura-panel aura-panel-interactive aura-glow overflow-hidden p-4 sm:p-5">
      <div className="flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-[0.18em] text-[var(--aura-text-faint)]">
          {label}
        </p>
        <Icon
          className="h-3.5 w-3.5"
          strokeWidth={1.6}
          style={{ color: accent === "positive" ? "#4ade80" : "#f87171", opacity: 0.7 }}
        />
      </div>

      <div className="mt-3 text-[var(--aura-text)]">{value}</div>

      <p className="mt-1.5 text-[11px] text-[var(--aura-text-faint)]">{footnote}</p>
    </div>
  );
}
