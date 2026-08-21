import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, CheckCircle2, Circle, Star } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  useAddChecklistItem,
  useChecklistDetail,
  useDeleteChecklist,
  useDeleteChecklistItem,
  useUpdateChecklistItem,
} from "@/hooks/useGoals";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

export function ChecklistDetailPage() {
  const { checklistId } = useParams<{ checklistId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: checklist, isLoading } = useChecklistDetail(checklistId);
  const addItem = useAddChecklistItem();
  const updateItem = useUpdateChecklistItem();
  const deleteItem = useDeleteChecklistItem();
  const deleteChecklist = useDeleteChecklist();

  const [newItem, setNewItem] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(false);

  if (isLoading || !checklist) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <SkeletonCard />
      </div>
    );
  }

  const addNewItem = () => {
    if (!newItem.trim()) return;
    addItem.mutate({ checklistId: checklist.id, name: newItem.trim() });
    setNewItem("");
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/goals/checklists" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Trackers
      </Link>

      <Card className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">{checklist.title}</h1>
            {checklist.description && <p className="text-sm text-[var(--text-secondary)]">{checklist.description}</p>}
          </div>
          <Button size="sm" variant="ghost" className="text-[var(--negative)]" onClick={() => setDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>

        <p className="mt-4 text-3xl font-bold text-[var(--text-primary)]">
          {checklist.completed_count}
          <span className="text-lg font-normal text-[var(--text-tertiary)]">
            /{checklist.target_count ?? checklist.item_count} completed
          </span>
        </p>
        <ProgressBar value={checklist.progress_percent} className="mt-2" />
      </Card>

      <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
        {checklist.items.map((item) => (
          <div key={item.id} className="flex items-center gap-3 p-4">
            <button onClick={() => updateItem.mutate({ id: item.id, is_completed: !item.is_completed })}>
              {item.is_completed ? (
                <CheckCircle2 className="h-5 w-5 text-[var(--positive)]" />
              ) : (
                <Circle className="h-5 w-5 text-[var(--text-tertiary)]" />
              )}
            </button>
            <div className="min-w-0 flex-1">
              <p className={cn("text-sm", item.is_completed ? "text-[var(--text-tertiary)] line-through" : "text-[var(--text-primary)]")}>
                {item.name}
              </p>
              {item.location && <p className="text-xs text-[var(--text-tertiary)]">{item.location}</p>}
            </div>
            {item.is_completed && (
              <div className="flex gap-0.5">
                {Array.from({ length: 5 }, (_, i) => (
                  <button key={i} onClick={() => updateItem.mutate({ id: item.id, rating: i + 1 })}>
                    <Star
                      className={cn(
                        "h-3.5 w-3.5",
                        item.rating && i < item.rating ? "fill-[var(--warning)] text-[var(--warning)]" : "text-[var(--border-default)]",
                      )}
                    />
                  </button>
                ))}
              </div>
            )}
            <button
              onClick={() => deleteItem.mutate(item.id)}
              className="rounded-lg p-1 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}

        <div className="flex items-center gap-2 p-4">
          <Input
            placeholder="Add an item..."
            value={newItem}
            onChange={(e) => setNewItem(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addNewItem()}
          />
          <Button size="icon" variant="secondary" onClick={addNewItem}>
            <Plus className="h-4 w-4" />
          </Button>
        </div>
      </Card>

      <ConfirmDialog
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
        title="Delete this tracker?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          try {
            await deleteChecklist.mutateAsync(checklist.id);
            toast({ title: "Tracker deleted", variant: "success" });
            navigate("/goals/checklists");
          } catch (error) {
            toast({ title: "Could not delete tracker", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}
