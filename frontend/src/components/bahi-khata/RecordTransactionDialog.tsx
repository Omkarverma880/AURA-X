import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select } from "@/components/ui/Input";
import { useAddTransaction } from "@/hooks/useBahiKhata";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";
import type { LedgerEntryDetail } from "@/types";

const schema = z.object({
  txn_type: z.enum(["repayment", "interest", "write_off"]),
  amount: z.coerce.number().positive("Enter an amount greater than zero."),
  txn_date: z.string(),
  method: z.string().optional(),
  description: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function RecordTransactionDialog({
  open,
  onClose,
  entry,
}: {
  open: boolean;
  onClose: () => void;
  entry: LedgerEntryDetail;
}) {
  const { toast } = useToast();
  const addTransaction = useAddTransaction();
  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { txn_type: "repayment", txn_date: new Date().toISOString().slice(0, 10) },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await addTransaction.mutateAsync({ entryId: entry.id, ...values });
      toast({ title: "Transaction recorded", variant: "success" });
      handleClose();
    } catch (error) {
      toast({
        title: "Could not record transaction",
        description: isApiError(error) ? error.message : undefined,
        variant: "error",
      });
    }
  };

  const verb = entry.direction === "given" ? "Received" : "Paid";

  return (
    <Dialog open={open} onClose={handleClose} title={`Record a ${verb.toLowerCase()} amount`}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Controller
          control={control}
          name="txn_type"
          render={({ field }) => (
            <Select value={field.value} onChange={(e) => field.onChange(e.target.value)}>
              <option value="repayment">{verb}</option>
              <option value="interest">Interest added</option>
              <option value="write_off">Write off (forgiven)</option>
            </Select>
          )}
        />

        <div>
          <Label htmlFor="amount">
            Amount <span className="text-[var(--text-tertiary)]">(outstanding: {entry.outstanding})</span>
          </Label>
          <Input id="amount" type="number" step="0.01" min="0" {...register("amount")} error={!!errors.amount} />
          <FieldError>{errors.amount?.message}</FieldError>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="txn_date">Date</Label>
            <Input id="txn_date" type="date" {...register("txn_date")} />
          </div>
          <div>
            <Label htmlFor="method">Method (optional)</Label>
            <Select {...register("method")}>
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
          <Label htmlFor="description">Note (optional)</Label>
          <Input id="description" {...register("description")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Save
        </Button>
      </form>
    </Dialog>
  );
}
