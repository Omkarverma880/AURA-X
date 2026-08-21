import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, CheckCircle2, Circle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Input } from "@/components/ui/Input";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  useAddMilestone,
  useDeleteLifeGoal,
  useDeleteMilestone,
  useLifeGoalDetail,
  useUpdateLifeGoal,
  useUpdateMilestone,
} from "@/hooks/useGoals";
import { formatDate } from "@/lib/format";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

export function GoalDetailPage() {
  const { goalId } = useParams<{ goalId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: goal, isLoading } = useLifeGoalDetail(goalId);
  const updateGoal = useUpdateLifeGoal();
  const deleteGoal = useDeleteLifeGoal();
  const addMilestone = useAddMilestone();
  const updateMilestone = useUpdateMilestone();
  const deleteMilestone = useDeleteMilestone();

  const [newMilestone, setNewMilestone] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  if (isLoading || !goal) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <SkeletonCard />
      </div>
    );
  }

  const markComplete = async () => {
    try {
      await updateGoal.mutateAsync({ id: goal.id, status: "completed" });
      toast({ title: "Goal completed! 🎉", variant: "success" });
    } catch (error) {
      toast({ title: "Could not update goal", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/goals" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Goals
      </Link>

      <Card className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">{goal.title}</h1>
            {goal.category_name && <p className="text-sm text-[var(--text-tertiary)]">{goal.category_name}</p>}
          </div>
          <Badge variant={goal.status === "completed" ? "positive" : "neutral"}>{goal.status.replace("_", " ")}</Badge>
        </div>

        {goal.description && <p className="mt-3 text-sm text-[var(--text-secondary)]">{goal.description}</p>}

        <div className="mt-4">
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--text-secondary)]">Progress</span>
            <span className="font-medium text-[var(--text-primary)]">{goal.progress_percent.toFixed(0)}%</span>
          </div>
          <ProgressBar value={goal.progress_percent} className="mt-1.5" variant={goal.status === "completed" ? "positive" : "brand"} />
        </div>

        {goal.target_date && (
          <p className="mt-3 text-xs text-[var(--text-tertiary)]">
            Target: {formatDate(goal.target_date, "long")} {goal.is_overdue && <span className="text-[var(--negative)]">· overdue</span>}
          </p>
        )}

        <div className="mt-4 flex gap-2">
          {goal.status !== "completed" && (
            <Button size="sm" onClick={markComplete}><CheckCircle2 className="h-4 w-4" /> Mark complete</Button>
          )}
          <Button size="sm" variant="ghost" className="ml-auto text-[var(--negative)]" onClick={() => setDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </div>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Milestones</h2>
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {goal.milestones.map((milestone) => (
            <div key={milestone.id} className="flex items-center gap-3 p-4">
              <button
                onClick={() =>
                  updateMilestone.mutate({ id: milestone.id, is_completed: !milestone.is_completed })
                }
              >
                {milestone.is_completed ? (
                  <CheckCircle2 className="h-5 w-5 text-[var(--positive)]" />
                ) : (
                  <Circle className="h-5 w-5 text-[var(--text-tertiary)]" />
                )}
              </button>
              <p className={`flex-1 text-sm ${milestone.is_completed ? "text-[var(--text-tertiary)] line-through" : "text-[var(--text-primary)]"}`}>
                {milestone.title}
              </p>
              <button
                onClick={() => deleteMilestone.mutate(milestone.id)}
                className="rounded-lg p-1 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
          <div className="flex items-center gap-2 p-4">
            <Input
              placeholder="Add a milestone..."
              value={newMilestone}
              onChange={(e) => setNewMilestone(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newMilestone.trim()) {
                  addMilestone.mutate({ goalId: goal.id, title: newMilestone.trim() });
                  setNewMilestone("");
                }
              }}
            />
            <Button
              size="icon"
              variant="secondary"
              onClick={() => {
                if (newMilestone.trim()) {
                  addMilestone.mutate({ goalId: goal.id, title: newMilestone.trim() });
                  setNewMilestone("");
                }
              }}
            >
              <Plus className="h-4 w-4" />
            </Button>
          </div>
        </Card>
      </div>

      <ConfirmDialog
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
        title="Delete this goal?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          try {
            await deleteGoal.mutateAsync(goal.id);
            toast({ title: "Goal deleted", variant: "success" });
            navigate("/goals");
          } catch (error) {
            toast({ title: "Could not delete goal", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}
