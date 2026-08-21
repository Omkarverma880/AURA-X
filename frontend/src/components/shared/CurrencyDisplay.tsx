import { Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatMoney, formatMoneyCompact } from "@/lib/format";
import { useFinancial } from "@/contexts/FinancialContext";

interface CurrencyDisplayProps {
  /** Null/undefined means "the server withheld this because it's locked". */
  value: number | null | undefined;
  currency?: string;
  compact?: boolean;
  withDecimals?: boolean;
  className?: string;
  /** Force masking even if a value is present - used for Bahi Khata amounts
   * when the user has opted into masking those too. */
  forceMask?: boolean;
  /** Clicking a masked value prompts the Green PIN dialog. */
  clickToUnlock?: boolean;
  size?: "sm" | "md" | "lg" | "xl";
}

const SIZE_CLASSES = {
  sm: "text-sm",
  md: "text-base",
  lg: "text-xl font-semibold",
  xl: "text-3xl font-bold tracking-tight",
};

export function CurrencyDisplay({
  value,
  currency = "INR",
  compact = false,
  withDecimals = false,
  className,
  forceMask = false,
  clickToUnlock = true,
  size = "md",
}: CurrencyDisplayProps) {
  const { promptUnlock } = useFinancial();
  const masked = value === null || value === undefined || forceMask;

  if (masked) {
    return (
      <button
        type="button"
        disabled={!clickToUnlock}
        onClick={clickToUnlock ? () => promptUnlock() : undefined}
        className={cn(
          "inline-flex items-center gap-1.5 tracking-[0.2em] text-[var(--text-tertiary)]",
          clickToUnlock && "cursor-pointer hover:text-[var(--text-secondary)]",
          SIZE_CLASSES[size],
          className,
        )}
        title={clickToUnlock ? "Unlock with Green PIN" : undefined}
      >
        <span>&bull;&bull;&bull;&bull;&bull;&bull;</span>
        {clickToUnlock && <Eye className="h-[0.85em] w-[0.85em] opacity-60" />}
      </button>
    );
  }

  const formatted = compact ? formatMoneyCompact(value, currency) : formatMoney(value, currency, withDecimals);
  const isNegative = value < 0;

  return (
    <span
      className={cn(
        SIZE_CLASSES[size],
        isNegative ? "text-[var(--negative)]" : "text-[var(--text-primary)]",
        className,
      )}
    >
      {formatted}
    </span>
  );
}
