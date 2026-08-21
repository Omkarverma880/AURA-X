import { Lock } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useFinancial } from "@/contexts/FinancialContext";

interface FinancialLockProps {
  title?: string;
  description?: string;
}

/** Full-section lock screen for pages the backend refuses with 423 while
 * financial data is locked (income, investments, exports). */
export function FinancialLock({
  title = "This is confidential",
  description = "Enter your Green PIN to view salary, spending and investment details.",
}: FinancialLockProps) {
  const { promptUnlock } = useFinancial();

  return (
    <div className="flex flex-col items-center justify-center gap-4 rounded-2xl border border-dashed border-[var(--border-default)] bg-[var(--bg-surface)] px-6 py-16 text-center">
      <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
        <Lock className="h-8 w-8 text-[var(--brand)]" strokeWidth={1.75} />
      </div>
      <div className="space-y-1">
        <p className="text-base font-semibold text-[var(--text-primary)]">{title}</p>
        <p className="max-w-sm text-sm text-[var(--text-secondary)]">{description}</p>
      </div>
      <Button onClick={() => promptUnlock()}>Enter Green PIN</Button>
    </div>
  );
}
