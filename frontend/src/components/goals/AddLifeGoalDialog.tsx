import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, Textarea } from "@/components/ui/Input";
import { useCreateLifeGoal, useLifeGoalCategories } from "@/hooks/useGoals";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  title: z.string().min(1, "Name your goal."),
  category_id: z.string().optional(),
  description: z.string().optional(),
  target_date: z.string().optional(),
  priority: z.enum(["low", "medium", "high"]).optional(),
});
type FormValues = z.infer<typeof schema>;

export function AddLifeGoalDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const { data: categories } = useLifeGoalCategories();
  const createGoal = useCreateLifeGoal();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { priority: "medium" } });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createGoal.mutateAsync({ ...values, category_id: values.category_id || undefined });
      toast({ title: "Goal added", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not add goal", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Add a life goal">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="title">What do you want to achieve?</Label>
          <Input id="title" placeholder="e.g. Complete all 12 Jyotirlingas" {...register("title")} error={!!errors.title} />
          <FieldError>{errors.title?.message}</FieldError>
        </div>

        {!!categories?.length && (
          <div>
            <Label htmlFor="category_id">Category</Label>
            <Select id="category_id" {...register("category_id")}>
              <option value="">None</option>
              {categories.map((cat) => (
                <option key={cat.id} value={cat.id}>{cat.name}</option>
              ))}
            </Select>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="target_date">Target date (optional)</Label>
            <Input id="target_date" type="date" {...register("target_date")} />
          </div>
          <div>
            <Label htmlFor="priority">Priority</Label>
            <Select id="priority" {...register("priority")}>
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </Select>
          </div>
        </div>

        <div>
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea id="description" rows={2} {...register("description")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Add goal
        </Button>
      </form>
    </Dialog>
  );
}
