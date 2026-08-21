import { ChevronLeft, ChevronRight } from "lucide-react";

interface MonthPickerProps {
  value: string; // YYYY-MM-01
  onChange: (value: string) => void;
}

function shiftMonth(period: string, delta: number): string {
  const [year, month] = period.split("-").map(Number);
  const date = new Date(year, month - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-01`;
}

export function currentPeriod(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

export function MonthPicker({ value, onChange }: MonthPickerProps) {
  const [year, month] = value.split("-").map(Number);
  const label = new Date(year, month - 1, 1).toLocaleDateString("en-IN", { month: "long", year: "numeric" });

  return (
    <div className="flex items-center gap-1 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] p-1">
      <button
        type="button"
        onClick={() => onChange(shiftMonth(value, -1))}
        className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-inset)]"
        aria-label="Previous month"
      >
        <ChevronLeft className="h-4 w-4" />
      </button>
      <span className="min-w-32 text-center text-sm font-medium text-[var(--text-primary)]">{label}</span>
      <button
        type="button"
        onClick={() => onChange(shiftMonth(value, 1))}
        disabled={value >= currentPeriod()}
        className="rounded-lg p-1.5 text-[var(--text-secondary)] hover:bg-[var(--bg-inset)] disabled:opacity-30"
        aria-label="Next month"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}
