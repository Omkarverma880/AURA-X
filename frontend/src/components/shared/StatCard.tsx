import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { ArrowDownRight, ArrowUpRight } from "lucide-react";
import { Card } from "@/components/ui/Card";
import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: ReactNode;
  icon?: LucideIcon;
  iconClassName?: string;
  trend?: "up" | "down" | "flat" | null;
  trendLabel?: string;
  subtext?: string;
  onClick?: () => void;
  className?: string;
}

export function StatCard({
  label,
  value,
  icon: Icon,
  iconClassName,
  trend,
  trendLabel,
  subtext,
  onClick,
  className,
}: StatCardProps) {
  const Wrapper = onClick ? "button" : "div";
  return (
    <Card
      className={cn(
        "p-5 text-left",
        onClick && "transition-transform hover:-translate-y-0.5 hover:shadow-elevated cursor-pointer",
        className,
      )}
    >
      <Wrapper onClick={onClick} className="flex w-full flex-col gap-3 text-left">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-[var(--text-secondary)]">{label}</span>
          {Icon && (
            <div className={cn("flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--brand-soft)]", iconClassName)}>
              <Icon className="h-4.5 w-4.5 text-[var(--brand)]" strokeWidth={2} />
            </div>
          )}
        </div>
        <div className="text-2xl font-bold tracking-tight text-[var(--text-primary)]">{value}</div>
        {(subtext || trend) && (
          <div className="flex items-center gap-1.5 text-xs">
            {trend && trend !== "flat" && (
              <span
                className={cn(
                  "flex items-center gap-0.5 font-medium",
                  trend === "up" ? "text-[var(--positive)]" : "text-[var(--negative)]",
                )}
              >
                {trend === "up" ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
              </span>
            )}
            <span className="text-[var(--text-tertiary)]">{trendLabel ?? subtext}</span>
          </div>
        )}
      </Wrapper>
    </Card>
  );
}
