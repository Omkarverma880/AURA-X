import { useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, Textarea } from "@/components/ui/Input";
import { useCreateEntry } from "@/hooks/useBahiKhata";
import { usePeople } from "@/hooks/useBahiKhata";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  direction: z.enum(["given", "borrowed"]),
  person_name: z.string().min(1, "Enter a name."),
  purpose: z.string().min(1, "What is this for?"),
  amount: z.coerce.number().positive("Enter an amount greater than zero."),
  entry_date: z.string(),
  due_date: z.string().optional(),
  notes: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function AddEntryDialog({
  open,
  onClose,
  defaultDirection = "given",
}: {
  open: boolean;
  onClose: () => void;
  defaultDirection?: "given" | "borrowed";
}) {
  const { toast } = useToast();
  const createEntry = useCreateEntry();
  const { data: people } = usePeople();
  const [useExisting, setUseExisting] = useState(false);

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      direction: defaultDirection,
      entry_date: new Date().toISOString().slice(0, 10),
    },
  });

  const handleClose = () => {
    reset();
    setUseExisting(false);
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createEntry.mutateAsync({
        direction: values.direction,
        person_name: values.person_name,
        purpose: values.purpose,
        amount: values.amount,
        entry_date: values.entry_date,
        due_date: values.due_date || null,
        notes: values.notes,
      });
      toast({ title: "Entry added", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not add entry", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Add to Bahi Khata">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Controller
          control={control}
          name="direction"
          render={({ field }) => (
            <div className="flex rounded-xl bg-[var(--bg-inset)] p-1 text-sm">
              {(["given", "borrowed"] as const).map((option) => (
                <button
                  key={option}
                  type="button"
                  onClick={() => field.onChange(option)}
                  className={`flex-1 rounded-lg py-2.5 font-medium transition-colors ${
                    field.value === option
                      ? option === "given"
                        ? "bg-[var(--positive-soft)] text-[var(--positive-soft-text)]"
                        : "bg-[var(--negative-soft)] text-[var(--negative-soft-text)]"
                      : "text-[var(--text-tertiary)]"
                  }`}
                >
                  {option === "given" ? "Money Given" : "Money Borrowed"}
                </button>
              ))}
            </div>
          )}
        />

        <div>
          <Label htmlFor="person_name">{useExisting ? "Choose a person" : "Person's name"}</Label>
          {useExisting ? (
            <Select {...register("person_name")}>
              <option value="">Select...</option>
              {people?.map((p) => (
                <option key={p.id} value={p.name}>
                  {p.name}
                </option>
              ))}
            </Select>
          ) : (
            <Input id="person_name" placeholder="e.g. Parbhu" {...register("person_name")} error={!!errors.person_name} />
          )}
          {!!people?.length && (
            <button
              type="button"
              onClick={() => setUseExisting((v) => !v)}
              className="mt-1.5 text-xs text-[var(--brand)] hover:underline"
            >
              {useExisting ? "Enter a new name instead" : "Pick from existing people"}
            </button>
          )}
          <FieldError>{errors.person_name?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="purpose">Purpose</Label>
          <Input id="purpose" placeholder="e.g. Tungnath trip" {...register("purpose")} error={!!errors.purpose} />
          <FieldError>{errors.purpose?.message}</FieldError>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="amount">Amount</Label>
            <Input id="amount" type="number" step="0.01" min="0" {...register("amount")} error={!!errors.amount} />
            <FieldError>{errors.amount?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="entry_date">Date</Label>
            <Input id="entry_date" type="date" {...register("entry_date")} />
          </div>
        </div>

        <div>
          <Label htmlFor="due_date">Due date (optional)</Label>
          <Input id="due_date" type="date" {...register("due_date")} />
        </div>

        <div>
          <Label htmlFor="notes">Notes (optional)</Label>
          <Textarea id="notes" rows={2} {...register("notes")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Add entry
        </Button>
      </form>
    </Dialog>
  );
}
