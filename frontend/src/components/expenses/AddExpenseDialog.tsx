import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, Textarea } from "@/components/ui/Input";
import { useCategories, useCreateExpense } from "@/hooks/useExpenses";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  amount: z.coerce.number().positive("Enter an amount greater than zero."),
  spent_on: z.string(),
  category_id: z.string().optional(),
  merchant: z.string().optional(),
  payment_method: z.string().optional(),
  description: z.string().optional(),
  is_recurring: z.boolean().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function AddExpenseDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const { data: categories } = useCategories({ kind: "expense" });
  const createExpense = useCreateExpense();

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { spent_on: new Date().toISOString().slice(0, 10), is_recurring: false },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createExpense.mutateAsync({
        ...values,
        category_id: values.category_id || undefined,
        recurrence: values.is_recurring ? "monthly" : "none",
      });
      toast({ title: "Expense added", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not add expense", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Add expense">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="amount">Amount</Label>
            <Input id="amount" type="number" step="0.01" min="0" {...register("amount")} error={!!errors.amount} />
            <FieldError>{errors.amount?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="spent_on">Date</Label>
            <Input id="spent_on" type="date" {...register("spent_on")} />
          </div>
        </div>

        <div>
          <Label htmlFor="category_id">Category</Label>
          <Select id="category_id" {...register("category_id")}>
            <option value="">Uncategorised</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>
                {cat.name}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="merchant">Merchant (optional)</Label>
            <Input id="merchant" {...register("merchant")} />
          </div>
          <div>
            <Label htmlFor="payment_method">Payment method</Label>
            <Select id="payment_method" {...register("payment_method")}>
              <option value="">Select...</option>
              <option value="cash">Cash</option>
              <option value="upi">UPI</option>
              <option value="bank_transfer">Bank transfer</option>
              <option value="card">Card</option>
              <option value="cheque">Cheque</option>
              <option value="other">Other</option>
            </Select>
          </div>
        </div>

        <div>
          <Label htmlFor="description">Description (optional)</Label>
          <Textarea id="description" rows={2} {...register("description")} />
        </div>

        <Controller
          control={control}
          name="is_recurring"
          render={({ field }) => (
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={field.value ?? false}
                onChange={(e) => field.onChange(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--border-default)] accent-[var(--brand)]"
              />
              This is a recurring monthly expense
            </label>
          )}
        />

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Add expense
        </Button>
      </form>
    </Dialog>
  );
}
