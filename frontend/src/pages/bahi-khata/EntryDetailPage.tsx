import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Ban, CheckCircle2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Avatar } from "@/components/ui/Avatar";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { RecordTransactionDialog } from "@/components/bahi-khata/RecordTransactionDialog";
import {
  useEntryDetail,
  useSettleEntry,
  useVoidTransaction,
  useDeleteEntry,
} from "@/hooks/useBahiKhata";
import { formatDate } from "@/lib/format";
import { useToast } from "@/contexts/ToastContext";
import { useFinancial } from "@/contexts/FinancialContext";
import { isApiError } from "@/lib/api";

export function EntryDetailPage() {
  const { entryId } = useParams<{ entryId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: entry, isLoading } = useEntryDetail(entryId);
  const settleEntry = useSettleEntry();
  const voidTransaction = useVoidTransaction();
  const deleteEntry = useDeleteEntry();

  const [recordOpen, setRecordOpen] = useState(false);
  const [settleConfirm, setSettleConfirm] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const [voidTarget, setVoidTarget] = useState<string | null>(null);
  const { isUnlocked, isPinConfigured, promptUnlock } = useFinancial();

  /** Same Green PIN gate as the person ledger: the server enforces it, this
   *  just asks for the PIN up front instead of letting the call 423. */
  const askToVoid = (txnId: string) => {
    if (isPinConfigured && !isUnlocked) {
      promptUnlock(() => setVoidTarget(txnId));
      return;
    }
    setVoidTarget(txnId);
  };

  if (isLoading || !entry) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const isGiven = entry.direction === "given";

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/bahi-khata" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Bahi Khata
      </Link>

      <Card className="overflow-hidden">
        <div className={isGiven ? "bg-[var(--positive-soft)] p-5" : "bg-[var(--negative-soft)] p-5"}>
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-3">
              <Avatar name={entry.person_name ?? "?"} />
              <div>
                <Link to={`/bahi-khata/people/${entry.person_id}`} className="font-semibold text-[var(--text-primary)] hover:underline">
                  {entry.person_name}
                </Link>
                <p className="text-sm text-[var(--text-secondary)]">{entry.purpose}</p>
              </div>
            </div>
            <Badge variant={statusVariant(entry.status)}>{entry.status}</Badge>
          </div>

          <div className="mt-5">
            <CurrencyDisplay value={entry.outstanding} size="xl" clickToUnlock={false} />
            <p className="text-xs text-[var(--text-tertiary)]">
              {isGiven ? "outstanding to receive" : "outstanding to pay"}
            </p>
            {entry.status === "partial" && <ProgressBar value={entry.progress_percent} className="mt-3" />}
          </div>
        </div>

        <CardContent className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Principal</p>
            <CurrencyDisplay value={entry.principal_amount} clickToUnlock={false} />
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Settled</p>
            <CurrencyDisplay value={entry.settled_amount} clickToUnlock={false} />
          </div>
          <div>
            <p className="text-xs text-[var(--text-tertiary)]">Due date</p>
            <p className="text-[var(--text-primary)]">{entry.due_date ? formatDate(entry.due_date) : "-"}</p>
          </div>
        </CardContent>

        {entry.notes && (
          <CardContent className="pt-0 text-sm text-[var(--text-secondary)]">{entry.notes}</CardContent>
        )}

        <div className="flex flex-wrap gap-2 border-t border-[var(--border-subtle)] p-4">
          {entry.outstanding > 0 && (
            <>
              <Button onClick={() => setRecordOpen(true)}>
                <Plus className="h-4 w-4" /> Record {isGiven ? "repayment" : "payment"}
              </Button>
              <Button variant="secondary" onClick={() => setSettleConfirm(true)}>
                <CheckCircle2 className="h-4 w-4" /> Settle in full
              </Button>
            </>
          )}
          <Button variant="ghost" className="ml-auto text-[var(--negative)]" onClick={() => setDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" /> Delete
          </Button>
        </div>
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Transaction history</h2>
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {entry.transactions.map((txn) => (
            <div key={txn.id} className={`flex items-center gap-3 p-4 ${txn.is_voided ? "opacity-50" : ""}`}>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium capitalize text-[var(--text-primary)]">
                  {txn.txn_type.replace("_", " ")}
                  {txn.is_voided && <span className="ml-2 text-xs font-normal text-[var(--negative)]">(voided)</span>}
                </p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {formatDate(txn.txn_date)} {txn.method ? `· ${txn.method}` : ""}
                  {txn.description ? ` · ${txn.description}` : ""}
                </p>
                {txn.is_voided && txn.void_reason && (
                  <p className="text-xs text-[var(--negative)]">Reason: {txn.void_reason}</p>
                )}
              </div>
              <CurrencyDisplay
                value={txn.signed_amount}
                clickToUnlock={false}
                className={txn.signed_amount >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}
              />
              {!txn.is_voided && txn.txn_type !== "principal" && (
                <button
                  type="button"
                  onClick={() => askToVoid(txn.id)}
                  className="rounded-lg p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
                  title="Void this transaction"
                >
                  <Ban className="h-4 w-4" />
                </button>
              )}
            </div>
          ))}
        </Card>
      </div>

      <RecordTransactionDialog open={recordOpen} onClose={() => setRecordOpen(false)} entry={entry} />

      <ConfirmDialog
        open={settleConfirm}
        onClose={() => setSettleConfirm(false)}
        title="Settle this entry in full?"
        description={`This records a final payment of the remaining ${entry.outstanding} and closes the entry.`}
        confirmLabel="Settle"
        onConfirm={async () => {
          try {
            await settleEntry.mutateAsync(entry.id);
            toast({ title: "Entry settled", variant: "success" });
          } catch (error) {
            toast({ title: "Could not settle entry", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />

      <ConfirmDialog
        open={deleteConfirm}
        onClose={() => setDeleteConfirm(false)}
        title="Delete this entry?"
        description="This voids every transaction on it. This cannot be undone."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={async () => {
          try {
            await deleteEntry.mutateAsync(entry.id);
            toast({ title: "Entry deleted", variant: "success" });
            navigate("/bahi-khata");
          } catch (error) {
            toast({ title: "Could not delete entry", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />

      <ConfirmDialog
        open={!!voidTarget}
        onClose={() => setVoidTarget(null)}
        title="Void this transaction?"
        description="It stays visible in the history, marked as voided, and the balance is restored."
        confirmLabel="Void"
        variant="danger"
        onConfirm={async () => {
          if (!voidTarget) return;
          try {
            await voidTransaction.mutateAsync({ txnId: voidTarget, reason: "Voided from entry detail" });
            toast({ title: "Transaction voided", variant: "success" });
          } catch (error) {
            toast({ title: "Could not void transaction", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}
