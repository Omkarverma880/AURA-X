import { type HTMLAttributes } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium leading-none",
  {
    variants: {
      variant: {
        neutral: "bg-[var(--bg-inset)] text-[var(--text-secondary)]",
        brand: "bg-[var(--brand-soft)] text-[var(--brand-soft-text)]",
        positive: "bg-[var(--positive-soft)] text-[var(--positive-soft-text)]",
        negative: "bg-[var(--negative-soft)] text-[var(--negative-soft-text)]",
        warning: "bg-[var(--warning-soft)] text-[var(--warning-soft-text)]",
        info: "bg-[var(--info-soft)] text-[var(--info-soft-text)]",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

export function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

/** Maps ledger/budget status strings straight to a semantic badge variant. */
export function statusVariant(status: string): BadgeProps["variant"] {
  switch (status) {
    case "settled":
    case "on_track":
    case "completed":
      return "positive";
    case "overdue":
    case "exceeded":
      return "negative";
    case "partial":
    case "warning":
    case "in_progress":
      return "warning";
    default:
      return "neutral";
  }
}
