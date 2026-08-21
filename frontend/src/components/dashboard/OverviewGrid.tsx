import { Link } from "react-router-dom";
import { HandCoins, Wallet, ArrowUpRight, ArrowDownRight, type LucideIcon } from "lucide-react";

import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { useFinancial } from "@/contexts/FinancialContext";
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
        to="/bahi-khata"
        value={snapshot.to_receive}
        footnote={snapshot.money_given > 0 ? "Outstanding receivable" : "Nothing lent yet"}
      />
      <OverviewTile
        label="You owe"
        icon={Wallet}
        accent="negative"
        to="/bahi-khata"
        value={snapshot.to_pay}
        footnote={snapshot.money_borrowed > 0 ? "Outstanding payable" : "Nothing borrowed"}
      />
      <OverviewTile
        label="Monthly income"
        icon={ArrowUpRight}
        accent="positive"
        to="/expenses/income"
        value={snapshot.monthly_income}
        footnote="This month"
      />
      <OverviewTile
        label="Monthly spend"
        icon={ArrowDownRight}
        accent="negative"
        to="/expenses"
        value={snapshot.monthly_expenses}
        footnote="This month"
      />
    </div>
  );
}

const TILE_CLASS =
  "aura-panel aura-panel-interactive aura-glow block w-full overflow-hidden p-4 text-left sm:p-5";

/**
 * A tile whose behaviour follows its own state.
 *
 * Unlocked, it is a link to the page behind the number. Locked, the number is
 * not readable, so the only useful action is to unlock - and it becomes a
 * button that prompts for the Green PIN. That split also keeps the markup
 * valid: CurrencyDisplay renders its masked state as a <button>, and nesting
 * that inside an <a> would be invalid HTML and swallow the unlock click.
 */
function OverviewTile({
  label,
  icon: Icon,
  value,
  footnote,
  accent,
  to,
}: {
  label: string;
  icon: LucideIcon;
  value: number | null | undefined;
  footnote: string;
  accent: "positive" | "negative";
  to: string;
}) {
  const { promptUnlock } = useFinancial();
  const locked = value === null || value === undefined;

  const body = (
    <>
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

      <div className="mt-3 text-[var(--aura-text)]">
        <CurrencyDisplay value={value} compact clickToUnlock={false} size="lg" />
      </div>

      <p className="mt-1.5 text-[11px] text-[var(--aura-text-faint)]">
        {locked ? "Unlock to view" : footnote}
      </p>
    </>
  );

  if (locked) {
    return (
      <button type="button" onClick={() => promptUnlock()} className={`${TILE_CLASS} cursor-pointer`}>
        {body}
      </button>
    );
  }

  return (
    <Link to={to} className={TILE_CLASS}>
      {body}
    </Link>
  );
}
