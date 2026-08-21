import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, FieldHint } from "@/components/ui/Input";
import { useRecordPersonPayment } from "@/hooks/useBahiKhata";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const schema = z.object({
  amount: z.coerce.number().positive("Enter an amount greater than zero."),
  txn_date: z.string(),
  description: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

/**
 * Settle money against a person rather than one specific loan - the way a
 * bahi khata is actually kept. The server applies the amount to that person's
 * oldest open entry first, spilling into the next as each is cleared, so the
 * user never has to remember which loan a repayment belonged to.
 */
export function RecordPersonPaymentDialog({
  open,
  onClose,
  personId,
  personName,
  direction,
  outstanding,
}: {
  open: boolean;
  onClose: () => void;
  personId: string;
  personName: string;
  /** "given" = money coming back to you; "borrowed" = money you are repaying. */
  direction: "given" | "borrowed";
  outstanding: number;
}) {
  const { toast } = useToast();
  const recordPayment = useRecordPersonPayment();
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { txn_date: new Date().toISOString().slice(0, 10) },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await recordPayment.mutateAsync({ personId, direction, ...values });
      toast({
        title: direction === "given" ? "Payment received" : "Payment recorded",
        variant: "success",
      });
      handleClose();
    } catch (error) {
      toast({
        title: "Could not record payment",
        description: isApiError(error) ? error.message : undefined,
        variant: "error",
      });
    }
  };

  const title =
    direction === "given"
      ? `Received from ${personName}`
      : `Paid back to ${personName}`;

  return (
    <Dialog open={open} onClose={handleClose} title={title}>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="amount">
            Amount{" "}
            <span className="text-[var(--text-tertiary)]">
              (outstanding: {outstanding})
            </span>
          </Label>
          <Input
            id="amount"
            type="number"
            step="0.01"
            inputMode="decimal"
            autoFocus
            {...register("amount")}
            error={!!errors.amount}
          />
          <FieldHint>
            Applied to the oldest unpaid entry first, then the next.
          </FieldHint>
          <FieldError>{errors.amount?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="txn_date">Date</Label>
          <Input id="txn_date" type="date" {...register("txn_date")} />
          <FieldError>{errors.txn_date?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="description">Note (optional)</Label>
          <Input id="description" {...register("description")} />
        </div>

        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" loading={isSubmitting}>
            Record
          </Button>
        </div>
      </form>
    </Dialog>
  );
}
