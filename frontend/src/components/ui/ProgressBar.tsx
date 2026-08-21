import { cn } from "@/lib/utils";

interface ProgressBarProps {
  value: number; // 0-100
  variant?: "brand" | "positive" | "warning" | "negative";
  className?: string;
  trackClassName?: string;
}

const COLORS: Record<NonNullable<ProgressBarProps["variant"]>, string> = {
  brand: "bg-[var(--brand)]",
  positive: "bg-[var(--positive)]",
  warning: "bg-[var(--warning)]",
  negative: "bg-[var(--negative)]",
};

export function ProgressBar({ value, variant = "brand", className, trackClassName }: ProgressBarProps) {
  const clamped = Math.min(Math.max(value, 0), 100);
  return (
    <div
      className={cn("h-2 w-full overflow-hidden rounded-full bg-[var(--bg-inset)]", trackClassName)}
      role="progressbar"
      aria-valuenow={clamped}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        className={cn("h-full rounded-full transition-[width] duration-500 ease-out", COLORS[variant], className)}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
