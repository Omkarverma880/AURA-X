import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Plus, Trash2, PencilLine } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { AddInvestmentTxnDialog } from "@/components/investments/AddInvestmentTxnDialog";
import {
  useDeleteHolding,
  useDeleteInvestmentTxn,
  useHoldingDetail,
  useUpdateHolding,
} from "@/hooks/useInvestments";
import { formatDate, formatPercent } from "@/lib/format";
import { ASSET_TYPE_LABELS } from "@/lib/investment-meta";
import { useToast } from "@/contexts/ToastContext";
import { isApiError } from "@/lib/api";

export function HoldingDetailPage() {
  const { holdingId } = useParams<{ holdingId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: holding, isLoading } = useHoldingDetail(holdingId);
  const updateHolding = useUpdateHolding();
  const deleteHolding = useDeleteHolding();
  const deleteTxn = useDeleteInvestmentTxn();

  const [addOpen, setAddOpen] = useState(false);
  const [editingPrice, setEditingPrice] = useState(false);
  const [priceInput, setPriceInput] = useState("");
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [deleteTxnId, setDeleteTxnId] = useState<string | null>(null);

  if (isLoading || !holding) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const savePrice = async () => {
    const price = Number(priceInput);
    if (!price || price <= 0) return;
    try {
      await updateHolding.mutateAsync({ id: holding.id, current_price: price });
      toast({ title: "Price updated", variant: "success" });
      setEditingPrice(false);
    } catch (error) {
      toast({ title: "Could not update price", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/investments" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Investments
      </Link>

      <Card className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-[var(--text-primary)]">{holding.name}</h1>
            <p className="text-sm text-[var(--text-tertiary)]">{ASSET_TYPE_LABELS[holding.asset_type] ?? holding.asset_type}</p>
          </div>
          <span className={`text-sm font-semibold ${holding.return_percent >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}`}>
            {formatPercent(holding.return_percent, true)}
          </span>
        </div>

        <div className="mt-4">
          <CurrencyDisplay value={holding.current_value} size="xl" />
          <p className="text-xs text-[var(--text-tertiary)]">current value</p>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Invested</p>
            <CurrencyDisplay value={holding.invested_amount} compact />
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Units held</p>
            <p className="font-medium text-[var(--text-primary)]">{holding.units_held}</p>
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Avg. price</p>
            <CurrencyDisplay value={holding.avg_price} compact />
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">XIRR</p>
            <p className="font-medium text-[var(--text-primary)]">
              {holding.xirr_percent !== null ? formatPercent(holding.xirr_percent) : "-"}
            </p>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-2 rounded-xl bg-[var(--bg-inset)] p-3">
          <span className="text-sm text-[var(--text-secondary)]">Current price</span>
          {editingPrice ? (
            <>
              <Input
                type="number"
                step="0.01"
                autoFocus
                className="h-8 w-28"
                value={priceInput}
                onChange={(e) => setPriceInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && savePrice()}
              />
              <Button size="sm" onClick={savePrice}>Save</Button>
              <Button size="sm" variant="ghost" onClick={() => setEditingPrice(false)}>Cancel</Button>
            </>
          ) : (
            <button
              className="ml-auto flex items-center gap-1.5 text-sm font-medium text-[var(--brand)]"
              onClick={() => { setPriceInput(String(holding.current_price ?? "")); setEditingPrice(true); }}
            >
              <CurrencyDisplay value={holding.current_price} compact clickToUnlock={false} className="font-medium text-[var(--brand)]" />
              <PencilLine className="h-3.5 w-3.5" />
            </button>
          )}
        </div>

        <div className="mt-4 flex gap-2">
          <Button onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> Record transaction</Button>
          <Button variant="ghost" className="ml-auto text-[var(--negative)]" onClick={() => setDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </div>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Transactions</h2>
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {holding.transactions.map((txn) => (
            <div key={txn.id} className="flex items-center gap-3 p-4">
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium capitalize text-[var(--text-primary)]">{txn.txn_type.replace("_", " ")}</p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {formatDate(txn.txn_date, "short")}
                  {txn.units ? ` · ${txn.units} units @ ${txn.price_per_unit}` : ""}
                </p>
              </div>
              <CurrencyDisplay value={txn.amount} clickToUnlock={false} />
              <button
                onClick={() => setDeleteTxnId(txn.id)}
                className="rounded-lg p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          ))}
        </Card>
      </div>

      {holding.notes && <CardContent className="p-0 text-sm text-[var(--text-secondary)]">{holding.notes}</CardContent>}

      <AddInvestmentTxnDialog open={addOpen} onClose={() => setAddOpen(false)} holdingId={holding.id} />

      <ConfirmDialog
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
        title="Delete this holding?"
        description="It will be archived and removed from your active portfolio."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={async () => {
          try {
            await deleteHolding.mutateAsync(holding.id);
            toast({ title: "Holding removed", variant: "success" });
            navigate("/investments");
          } catch (error) {
            toast({ title: "Could not remove holding", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />

      <ConfirmDialog
        open={!!deleteTxnId}
        onClose={() => setDeleteTxnId(null)}
        title="Delete this transaction?"
        variant="danger"
        confirmLabel="Delete"
        onConfirm={async () => {
          if (!deleteTxnId) return;
          try {
            await deleteTxn.mutateAsync(deleteTxnId);
            toast({ title: "Transaction deleted", variant: "success" });
          } catch (error) {
            toast({ title: "Could not delete transaction", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}
