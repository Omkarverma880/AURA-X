import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, Textarea, FieldHint } from "@/components/ui/Input";
import { useCreateChecklist } from "@/hooks/useGoals";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const TRACKER_TYPES = [
  ["generic", "Custom"],
  ["temple", "Temples / Pilgrimage"],
  ["trek", "Treks"],
  ["trip", "Trips"],
  ["country", "Countries"],
  ["book", "Books"],
  ["course", "Courses"],
  ["fitness", "Fitness"],
  ["achievement", "Achievements"],
] as const;

const schema = z.object({
  title: z.string().min(1, "Name your tracker."),
  tracker_type: z.string(),
  target_count: z.coerce.number().min(1).optional(),
  itemsText: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function AddChecklistDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const createChecklist = useCreateChecklist();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { tracker_type: "generic" },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    const items = (values.itemsText ?? "")
      .split("\n")
      .map((line) => line.trim())
      .filter(Boolean);
    try {
      await createChecklist.mutateAsync({
        title: values.title,
        tracker_type: values.tracker_type,
        target_count: values.target_count,
        items: items.length ? items : undefined,
      });
      toast({ title: "Tracker created", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not create tracker", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Create a tracker">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="title">Tracker name</Label>
          <Input id="title" placeholder="e.g. 12 Jyotirlingas" {...register("title")} error={!!errors.title} />
          <FieldError>{errors.title?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="tracker_type">Type</Label>
          <Select id="tracker_type" {...register("tracker_type")}>
            {TRACKER_TYPES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
        </div>

        <div>
          <Label htmlFor="target_count">Target count (optional)</Label>
          <Input id="target_count" type="number" min="1" {...register("target_count")} />
          <FieldHint>e.g. 20 if you plan 20 treks but are only logging a few so far.</FieldHint>
        </div>

        <div>
          <Label htmlFor="itemsText">Items (one per line, optional)</Label>
          <Textarea
            id="itemsText"
            rows={5}
            placeholder={"Somnath\nMallikarjuna\nMahakaleshwar\n..."}
            {...register("itemsText")}
          />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create tracker
        </Button>
      </form>
    </Dialog>
  );
}
