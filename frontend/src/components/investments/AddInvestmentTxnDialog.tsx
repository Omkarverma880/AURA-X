import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select } from "@/components/ui/Input";
import { useAddInvestmentTxn } from "@/hooks/useInvestments";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  txn_type: z.enum(["buy", "sell", "dividend", "interest", "fee", "bonus"]),
  units: z.coerce.number().min(0).optional(),
  amount: z.coerce.number().min(0, "Enter an amount."),
  price_per_unit: z.coerce.number().min(0).optional(),
  fees: z.coerce.number().min(0).optional(),
  txn_date: z.string(),
  notes: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

const NEEDS_UNITS = new Set(["buy", "sell", "bonus"]);

export function AddInvestmentTxnDialog({
  open,
  onClose,
  holdingId,
}: {
  open: boolean;
  onClose: () => void;
  holdingId: string;
}) {
  const { toast } = useToast();
  const addTxn = useAddInvestmentTxn();

  const {
    register,
    handleSubmit,
    control,
    watch,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { txn_type: "buy", txn_date: new Date().toISOString().slice(0, 10) },
  });

  const txnType = watch("txn_type");

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await addTxn.mutateAsync({ holdingId, ...values });
      toast({ title: "Transaction recorded", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not record transaction", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Record a transaction">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Controller
          control={control}
          name="txn_type"
          render={({ field }) => (
            <Select value={field.value} onChange={(e) => field.onChange(e.target.value)}>
              <option value="buy">Buy</option>
              <option value="sell">Sell</option>
              <option value="dividend">Dividend</option>
              <option value="interest">Interest</option>
              <option value="bonus">Bonus units</option>
              <option value="fee">Fee</option>
            </Select>
          )}
        />

        {NEEDS_UNITS.has(txnType ?? "buy") && (
          <div>
            <Label htmlFor="units">Units</Label>
            <Input id="units" type="number" step="0.0001" min="0" {...register("units")} error={!!errors.units} />
            <FieldError>{errors.units?.message}</FieldError>
          </div>
        )}

        <div>
          <Label htmlFor="amount">Amount</Label>
          <Input id="amount" type="number" step="0.01" min="0" {...register("amount")} error={!!errors.amount} />
          <FieldError>{errors.amount?.message}</FieldError>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="fees">Fees (optional)</Label>
            <Input id="fees" type="number" step="0.01" min="0" {...register("fees")} />
          </div>
          <div>
            <Label htmlFor="txn_date">Date</Label>
            <Input id="txn_date" type="date" {...register("txn_date")} />
          </div>
        </div>

        <div>
          <Label htmlFor="notes">Notes (optional)</Label>
          <Input id="notes" {...register("notes")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Save
        </Button>
      </form>
    </Dialog>
  );
}
