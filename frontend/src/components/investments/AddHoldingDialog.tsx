import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, Select, FieldHint } from "@/components/ui/Input";
import { useCreateHolding } from "@/hooks/useInvestments";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

const ASSET_TYPES = [
  ["stock", "Stock"],
  ["mutual_fund", "Mutual Fund"],
  ["etf", "ETF"],
  ["fixed_deposit", "Fixed Deposit"],
  ["gold", "Gold"],
  ["nps", "NPS"],
  ["ppf", "PPF"],
  ["epf", "EPF"],
  ["bond", "Bond"],
  ["real_estate", "Real Estate"],
  ["crypto", "Crypto"],
  ["other", "Other"],
] as const;

const schema = z.object({
  name: z.string().min(1, "Enter a name."),
  asset_type: z.string(),
  initial_units: z.coerce.number().positive("Enter the units purchased."),
  initial_amount: z.coerce.number().positive("Enter the amount invested."),
  purchase_date: z.string(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function AddHoldingDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const createHolding = useCreateHolding();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { asset_type: "mutual_fund", purchase_date: new Date().toISOString().slice(0, 10) },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createHolding.mutateAsync(values);
      toast({ title: "Holding added", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not add holding", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Add an investment">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="name">Name</Label>
          <Input id="name" placeholder="e.g. Nifty 50 Index Fund" {...register("name")} error={!!errors.name} />
          <FieldError>{errors.name?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="asset_type">Asset type</Label>
          <Select id="asset_type" {...register("asset_type")}>
            {ASSET_TYPES.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="initial_units">Units purchased</Label>
            <Input id="initial_units" type="number" step="0.0001" min="0" {...register("initial_units")} error={!!errors.initial_units} />
            <FieldHint>Use 1 for lump-sum assets like FDs.</FieldHint>
            <FieldError>{errors.initial_units?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="initial_amount">Amount invested</Label>
            <Input id="initial_amount" type="number" step="0.01" min="0" {...register("initial_amount")} error={!!errors.initial_amount} />
            <FieldError>{errors.initial_amount?.message}</FieldError>
          </div>
        </div>

        <div>
          <Label htmlFor="purchase_date">Purchase date</Label>
          <Input id="purchase_date" type="date" {...register("purchase_date")} />
        </div>

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Add holding
        </Button>
      </form>
    </Dialog>
  );
}
