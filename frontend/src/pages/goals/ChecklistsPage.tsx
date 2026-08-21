import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, ListChecks, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { CategoryIcon } from "@/components/shared/CategoryIcon";
import { AddChecklistDialog } from "@/components/goals/AddChecklistDialog";
import { useChecklists } from "@/hooks/useGoals";

export function ChecklistsPage() {
  const [addOpen, setAddOpen] = useState(false);
  const { data: checklists, isLoading } = useChecklists();

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <Link to="/goals" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
            <ArrowLeft className="h-4 w-4" /> Back to Goals
          </Link>
          <h1 className="mt-2 text-2xl font-bold text-[var(--text-primary)]">Trackers</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            Jyotirlingas, treks, books, countries - track whatever you're chasing.
          </p>
        </div>
        <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New tracker</Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }, (_, i) => <SkeletonCard key={i} />)}
        </div>
      ) : !checklists?.length ? (
        <Card>
          <EmptyState
            icon={ListChecks}
            title="No trackers yet"
            description="Create a checklist for the 12 Jyotirlingas, your trek bucket list, or anything else."
            action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New tracker</Button>}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {checklists.map((checklist) => (
            <Link key={checklist.id} to={`/goals/checklists/${checklist.id}`}>
              <Card className="h-full p-4 transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
                <div className="flex items-center gap-2.5">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-xl"
                    style={{ backgroundColor: `${checklist.color ?? "#8b5cf6"}22` }}
                  >
                    <CategoryIcon icon={checklist.icon} color={checklist.color} />
                  </div>
                  <p className="font-semibold text-[var(--text-primary)]">{checklist.title}</p>
                </div>
                <p className="mt-3 text-2xl font-bold text-[var(--text-primary)]">
                  {checklist.completed_count}
                  <span className="text-base font-normal text-[var(--text-tertiary)]">
                    /{checklist.target_count ?? checklist.item_count}
                  </span>
                </p>
                <ProgressBar value={checklist.progress_percent} className="mt-2" />
                <p className="mt-1.5 text-xs text-[var(--text-tertiary)]">{checklist.progress_percent.toFixed(0)}% complete</p>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <AddChecklistDialog open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  );
}
