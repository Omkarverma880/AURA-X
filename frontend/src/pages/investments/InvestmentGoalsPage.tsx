import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { ArrowLeft, Plus, Target, Trash2 } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Dialog } from "@/components/ui/Dialog";
import { Input, Label, FieldError } from "@/components/ui/Input";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { FinancialLock } from "@/components/shared/FinancialLock";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import {
  useCreateInvestmentGoal,
  useDeleteInvestmentGoal,
  useInvestmentGoals,
} from "@/hooks/useInvestments";
import { formatMoneyCompact } from "@/lib/format";
import { isApiError } from "@/lib/api";
import { useToast } from "@/contexts/ToastContext";
import type { InvestmentGoal } from "@/types";

const schema = z.object({
  name: z.string().min(1, "Name your goal."),
  target_amount: z.coerce.number().positive("Enter a target amount."),
  current_age: z.coerce.number().min(1).max(120).optional(),
  target_age: z.coerce.number().min(1).max(120).optional(),
  expected_return: z.coerce.number().min(0).max(50).optional(),
  monthly_investment: z.coerce.number().min(0).optional(),
  step_up_percent: z.coerce.number().min(0).max(100).optional(),
  use_portfolio_value: z.boolean().optional(),
});
type FormInput = z.input<typeof schema>;
type FormValues = z.output<typeof schema>;

export function InvestmentGoalsPage() {
  const [addOpen, setAddOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);
  const { data: goals, isLoading, error } = useInvestmentGoals();
  const deleteGoal = useDeleteInvestmentGoal();
  const { toast } = useToast();

  if (isApiError(error) && error.status === 423) {
    return (
      <div className="space-y-5">
        <BackLink />
        <FinancialLock title="Goal planner is confidential" description="Enter your Green PIN to plan your financial goals." />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <BackLink />
          <h1 className="mt-2 text-2xl font-bold text-[var(--text-primary)]">Investment Goal Planner</h1>
          <p className="text-sm text-[var(--text-secondary)]">
            "I want ₹5 crore by 45." We'll work out what that takes.
          </p>
        </div>
        <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New goal</Button>
      </div>

      {isLoading ? null : !goals?.length ? (
        <Card>
          <EmptyState
            icon={Target}
            title="Plan your first financial goal"
            description="Retirement, a house, financial freedom - set a target and we'll calculate the SIP you need."
            action={<Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> New goal</Button>}
          />
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {goals.map((goal) => (
            <GoalCard key={goal.id} goal={goal} onDelete={() => setDeleteTarget(goal.id)} />
          ))}
        </div>
      )}

      <AddGoalDialog open={addOpen} onClose={() => setAddOpen(false)} />

      <ConfirmDialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        title="Delete this goal?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deleteTarget) return;
          try {
            await deleteGoal.mutateAsync(deleteTarget);
            toast({ title: "Goal deleted", variant: "success" });
          } catch (e) {
            toast({ title: "Could not delete goal", description: isApiError(e) ? e.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}

function BackLink() {
  return (
    <Link to="/investments" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
      <ArrowLeft className="h-4 w-4" /> Back to Investments
    </Link>
  );
}

function GoalCard({ goal, onDelete }: { goal: InvestmentGoal; onDelete: () => void }) {
  return (
    <Card className="p-5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="font-semibold text-[var(--text-primary)]">{goal.name}</h3>
          <p className="text-xs text-[var(--text-tertiary)]">
            Target <CurrencyDisplay value={goal.target_amount} compact clickToUnlock={false} className="inline" /> in {goal.years_remaining.toFixed(1)} years
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={goal.on_track ? "positive" : "negative"}>{goal.on_track ? "On track" : "Needs more"}</Badge>
          <button onClick={onDelete} className="rounded-lg p-1 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]">
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="mt-4 h-40">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={goal.projection_chart}>
            <defs>
              <linearGradient id={`goal-${goal.id}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="var(--brand)" stopOpacity={0.35} />
                <stop offset="95%" stopColor="var(--brand)" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" vertical={false} />
            <XAxis dataKey="year" tick={{ fontSize: 11, fill: "var(--text-tertiary)" }} axisLine={false} tickLine={false} />
            <YAxis
              tickFormatter={(v) => formatMoneyCompact(v)}
              tick={{ fontSize: 11, fill: "var(--text-tertiary)" }}
              axisLine={false}
              tickLine={false}
              width={56}
            />
            <Tooltip formatter={(v) => formatMoneyCompact(Number(v))} labelFormatter={(y) => `Year ${y}`} />
            <Area type="monotone" dataKey="corpus" stroke="var(--brand)" fill={`url(#goal-${goal.id})`} strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-[var(--text-tertiary)]">Projected value</p>
          <CurrencyDisplay value={goal.projected_value} compact clickToUnlock={false} />
        </div>
        <div>
          <p className="text-xs text-[var(--text-tertiary)]">Required monthly SIP</p>
          <CurrencyDisplay value={goal.required_monthly_sip} compact clickToUnlock={false} className="text-[var(--brand)] font-semibold" />
        </div>
      </div>
    </Card>
  );
}

function AddGoalDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { toast } = useToast();
  const createGoal = useCreateInvestmentGoal();

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormInput, unknown, FormValues>({
    resolver: zodResolver(schema),
    defaultValues: { expected_return: 12, use_portfolio_value: true },
  });

  const handleClose = () => {
    reset();
    onClose();
  };

  const onSubmit = async (values: FormValues) => {
    try {
      await createGoal.mutateAsync(values);
      toast({ title: "Goal created", variant: "success" });
      handleClose();
    } catch (error) {
      toast({ title: "Could not create goal", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} title="Plan a new goal">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="name">Goal name</Label>
          <Input id="name" placeholder="e.g. Retirement, House, Financial Freedom" {...register("name")} error={!!errors.name} />
          <FieldError>{errors.name?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="target_amount">Target amount</Label>
          <Input id="target_amount" type="number" step="0.01" {...register("target_amount")} error={!!errors.target_amount} />
          <FieldError>{errors.target_amount?.message}</FieldError>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="current_age">Current age</Label>
            <Input id="current_age" type="number" {...register("current_age")} />
          </div>
          <div>
            <Label htmlFor="target_age">Target age</Label>
            <Input id="target_age" type="number" {...register("target_age")} error={!!errors.target_age} />
            <FieldError>{errors.target_age?.message}</FieldError>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label htmlFor="expected_return">Expected annual return %</Label>
            <Input id="expected_return" type="number" step="0.1" {...register("expected_return")} />
          </div>
          <div>
            <Label htmlFor="monthly_investment">Current monthly SIP</Label>
            <Input id="monthly_investment" type="number" step="0.01" {...register("monthly_investment")} />
          </div>
        </div>

        <div>
          <Label htmlFor="step_up_percent">Annual step-up % (optional)</Label>
          <Input id="step_up_percent" type="number" step="0.1" {...register("step_up_percent")} />
        </div>

        <Controller
          control={control}
          name="use_portfolio_value"
          render={({ field }) => (
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <input
                type="checkbox"
                checked={field.value ?? true}
                onChange={(e) => field.onChange(e.target.checked)}
                className="h-4 w-4 rounded border-[var(--border-default)] accent-[var(--brand)]"
              />
              Use my live investment portfolio value as the starting corpus
            </label>
          )}
        />

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Create goal
        </Button>
      </form>
    </Dialog>
  );
}
