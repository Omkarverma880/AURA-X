import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Plus, PiggyBank } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Input, Label, FieldError, Select } from "@/components/ui/Input";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { FinancialLock } from "@/components/shared/FinancialLock";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { CategoryIcon } from "@/components/shared/CategoryIcon";
import { MonthPicker, currentPeriod } from "@/components/shared/MonthPicker";
import { useBudgets, useCategories, useUpsertBudget } from "@/hooks/useExpenses";
import { isApiError } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";

const schema = z.object({
  category_id: z.string().min(1, "Choose a category."),
  amount: z.coerce.number().min(0, "Enter a budget amount."),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function BudgetsPage() {
  const [period, setPeriod] = useState(currentPeriod());
  const [addOpen, setAddOpen] = useState(false);
  const { data: budgets, isLoading, error } = useBudgets(period);

  if (isApiError(error) && error.status === 423) {
    return (
      <div className="space-y-5">
        <BackLink />
        <FinancialLock title="Budgets are confidential" description="Enter your Green PIN to view your budget plan." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <BackLink />
          <h1 className="mt-2 text-2xl font-bold text-[var(--text-primary)]">Budgets</h1>
          <p className="text-sm text-[var(--text-secondary)]">Set a monthly cap per category.</p>
        </div>
        <div className="flex items-center gap-2">
          <MonthPicker value={period} onChange={setPeriod} />
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Set budget
          </Button>
        </div>
      </div>

      {isLoading ? null : !budgets?.length ? (
        <Card>
          <EmptyState icon={PiggyBank} title="No budgets set for this month" description="Set a spending cap for a category to track it here." />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {budgets.map((budget) => (
            <Card key={budget.category_id} className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CategoryIcon icon={budget.category_icon} color={budget.category_color} />
                  <span className="text-sm font-semibold text-[var(--text-primary)]">{budget.category_name}</span>
                </div>
                <Badge variant={statusVariant(budget.status)}>{budget.status.replace("_", " ")}</Badge>
              </div>
              <div className="mt-3 flex items-baseline justify-between text-sm">
                <CurrencyDisplay value={budget.spent} clickToUnlock={false} />
                <span className="text-[var(--text-tertiary)]">of {budget.amount}</span>
              </div>
              <ProgressBar
                value={budget.utilisation}
                variant={budget.status === "exceeded" ? "negative" : budget.status === "warning" ? "warning" : "positive"}
                className="mt-2"
              />
              <p className="mt-2 text-xs text-[var(--text-tertiary)]">
                {budget.remaining >= 0 ? `₹${budget.remaining.toLocaleString("en-IN")} remaining` : `₹${Math.abs(budget.remaining).toLocaleString("en-IN")} over budget`}
              </p>
            </Card>
          ))}
        </div>
      )}

      <SetBudgetDialog open={addOpen} onClose={() => setAddOpen(false)} period={period} />
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

function SetBudgetDialog({ open, onClose, period }: { open: boolean; onClose: () => void; period: string }) {
  const { toast } = useToast();
  const { data: categories } = useCategories({ kind: "expense" });
  const upsertBudget = useUpsertBudget();

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({ resolver: zodResolver(schema) });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await upsertBudget.mutateAsync({ ...values, period_month: period });
      toast({ title: "Budget saved", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not save budget", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Set a budget">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="category_id">Category</Label>
          <Select id="category_id" {...register("category_id")} error={!!errors.category_id}>
            <option value="">Select...</option>
            {categories?.map((cat) => (
              <option key={cat.id} value={cat.id}>{cat.name}</option>
            ))}
          </Select>
          <FieldError>{errors.category_id?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="amount">Monthly budget</Label>
          <Input id="amount" type="number" step="0.01" min="0" {...register("amount")} error={!!errors.amount} />
          <FieldError>{errors.amount?.message}</FieldError>
        </div>
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Save budget
        </Button>
      </form>
    </Dialog>
  );
}
