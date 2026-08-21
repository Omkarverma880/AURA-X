import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Target, ListChecks, Calendar } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { AddLifeGoalDialog } from "@/components/goals/AddLifeGoalDialog";
import { useLifeGoals } from "@/hooks/useGoals";
import { formatDate } from "@/lib/format";

const PRIORITY_VARIANT = { high: "negative", medium: "warning", low: "neutral" } as const;

export function GoalsPage() {
  const [addOpen, setAddOpen] = useState(false);
  const { data: goals, isLoading } = useLifeGoals();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Life Goals</h1>
          <p className="text-sm text-[var(--text-secondary)]">The ambitions that make life more than a spreadsheet.</p>
        </div>
        <div className="flex gap-2">
          <Link to="/goals/checklists">
            <Button variant="secondary"><ListChecks className="h-4 w-4" /> Trackers</Button>
          </Link>
          <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New goal</Button>
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !goals?.length ? (
        <Card>
          <EmptyState
            icon={Target}
            title="No goals yet"
            description="From trekking every Himalayan peak to a 1 crore investment corpus - add what matters to you."
            action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New goal</Button>}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {goals.map((goal) => (
            <Link key={goal.id} to={`/goals/${goal.id}`}>
              <Card className="h-full p-4 transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
                <div className="flex items-start justify-between gap-2">
                  <p className="font-semibold text-[var(--text-primary)]">{goal.title}</p>
                  <Badge variant={PRIORITY_VARIANT[goal.priority]}>{goal.priority}</Badge>
                </div>
                {goal.category_name && <p className="text-xs text-[var(--text-tertiary)]">{goal.category_name}</p>}
                <ProgressBar value={goal.progress_percent} className="mt-3" variant={goal.status === "completed" ? "positive" : "brand"} />
                <div className="mt-2 flex items-center justify-between text-xs text-[var(--text-tertiary)]">
                  <span>{goal.progress_percent.toFixed(0)}% complete</span>
                  {goal.target_date && (
                    <span className={`flex items-center gap-1 ${goal.is_overdue ? "text-[var(--negative)]" : ""}`}>
                      <Calendar className="h-3 w-3" /> {formatDate(goal.target_date, "short")}
                    </span>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <AddLifeGoalDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
