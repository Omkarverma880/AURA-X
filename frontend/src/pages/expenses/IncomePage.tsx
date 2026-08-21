import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Plus, Wallet } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Input, Label, FieldError, Select } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { FinancialLock } from "@/components/shared/FinancialLock";
import {
  useCreateIncome,
  useCreateIncomeSource,
  useDeleteIncome,
  useIncome,
  useIncomeSources,
} from "@/hooks/useExpenses";
import { formatDate } from "@/lib/format";
import { isApiError } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";

const schema = z.object({
  source_id: z.string().optional(),
  received_on: z.string(),
  gross_amount: z.coerce.number().positive("Enter a gross amount."),
  net_amount: z.coerce.number().positive("Enter a net amount."),
  description: z.string().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function IncomePage() {
  const { data: income, isLoading, error } = useIncome({ page: 1, page_size: 50 });
  const { data: sources } = useIncomeSources();
  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const deleteIncome = useDeleteIncome();
  const { toast } = useToast();

  if (isApiError(error) && error.status === 423) {
    return (
      <div className="space-y-5">
        <BackLink />
        <FinancialLock title="Income is confidential" description="Enter your Green PIN to view salary and income records." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <BackLink />
          <h1 className="mt-2 text-2xl font-bold text-[var(--text-primary)]">Income</h1>
          <p className="text-sm text-[var(--text-secondary)]">Salary, bonuses and other income.</p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="h-4 w-4" /> Add income
        </Button>
      </div>

      {isLoading ? (
        <Card><SkeletonList rows={5} /></Card>
      ) : !income?.items.length ? (
        <Card>
          <EmptyState icon={Wallet} title="No income recorded yet" description="Add your salary or other income to start tracking savings." />
        </Card>
      ) : (
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {income.items.map((record) => (
            <div key={record.id} className="flex items-center gap-3 p-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-[var(--text-primary)]">
                  {record.source_name ?? "Income"}
                  {record.description ? ` · ${record.description}` : ""}
                </p>
                <p className="text-xs text-[var(--text-tertiary)]">{formatDate(record.received_on)}</p>
              </div>
              <div className="text-right">
                <CurrencyDisplay value={record.net_amount} />
                <p className="text-[10px] text-[var(--text-tertiary)]">net of {record.gross_amount}</p>
              </div>
              <button
                onClick={() => setDeleteTarget(record.id)}
                className="rounded-lg px-2 py-1 text-xs text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
              >
                Delete
              </button>
            </div>
          ))}
        </Card>
      )}

      <AddIncomeDialog open={addOpen} onClose={() => setAddOpen(false)} sourceIds={sources} />

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete this income record?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deleteTarget) return;
          try {
            await deleteIncome.mutateAsync(deleteTarget);
            toast({ title: "Income record deleted", variant: "success" });
          } catch (e) {
            toast({ title: "Could not delete record", description: isApiError(e) ? e.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/expenses" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
      <ArrowLeft className="h-4 w-4" /> Back to Expenses
    </Link>
  );
}

function AddIncomeDialog({
  open,
  onClose,
  sourceIds,
}: {
  open: boolean;
  onClose: () => void;
  sourceIds?: ReturnType<typeof useIncomeSources>["data"];
}) {
  const { toast } = useToast();
  const createIncome = useCreateIncome();
  const createSource = useCreateIncomeSource();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { received_on: new Date().toISOString().slice(0, 10) },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      let sourceId = values.source_id;
      if (!sourceId && !sourceIds?.length) {
        const created = await createSource.mutateAsync({ name: "Primary Income" });
        sourceId = created.id;
      }
      await createIncome.mutateAsync({ ...values, source_id: sourceId || undefined });
      toast({ title: "Income recorded", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not record income", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Add income">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        {!!sourceIds?.length && (
          <div>
            <Label htmlFor="source_id">Source</Label>
            <Select id="source_id" {...register("source_id")}>
              {sourceIds.map((s) => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </Select>
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="gross_amount">Gross amount</Label>
            <Input id="gross_amount" type="number" step="0.01" {...register("gross_amount")} error={!!errors.gross_amount} />
            <FieldError>{errors.gross_amount?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="net_amount">Net amount</Label>
            <Input id="net_amount" type="number" step="0.01" {...register("net_amount")} error={!!errors.net_amount} />
            <FieldError>{errors.net_amount?.message}</FieldError>
          </div>
        </div>
        <div>
          <Label htmlFor="received_on">Date received</Label>
          <Input id="received_on" type="date" {...register("received_on")} />
        </div>
        <div>
          <Label htmlFor="description">Description (optional)</Label>
          <Input id="description" {...register("description")} />
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Save
        </Button>
      </form>
    </Dialog>
  );
}
