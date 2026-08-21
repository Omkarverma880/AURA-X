import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, Phone, Mail, Plus, Archive, IndianRupee, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card, CardContent } from "@/components/ui/Card";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { SkeletonCard } from "@/components/ui/Skeleton";
import { Avatar } from "@/components/ui/Avatar";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { AddEntryDialog } from "@/components/bahi-khata/AddEntryDialog";
import { RecordTransactionDialog } from "@/components/bahi-khata/RecordTransactionDialog";
import { RecordPersonPaymentDialog } from "@/components/bahi-khata/RecordPersonPaymentDialog";
import { usePersonDetail, useDeletePerson, useVoidTransaction } from "@/hooks/useBahiKhata";
import { formatDate } from "@/lib/format";
import { useToast } from "@/contexts/ToastContext";
import { useFinancial } from "@/contexts/FinancialContext";
import { isApiError } from "@/lib/api";
import type { LedgerEntry } from "@/types";

export function PersonDetailPage() {
  const { personId } = useParams<{ personId: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { data: person, isLoading } = usePersonDetail(personId);
  const deletePerson = useDeletePerson();
  const [addOpen, setAddOpen] = useState(false);
  const [archiveConfirm, setArchiveConfirm] = useState(false);
  const [recordFor, setRecordFor] = useState<LedgerEntry | null>(null);
  const [payDirection, setPayDirection] = useState<"given" | "borrowed" | null>(null);
  const [voidTarget, setVoidTarget] = useState<string | null>(null);
  const voidTransaction = useVoidTransaction();
  const { isUnlocked, isPinConfigured, promptUnlock } = useFinancial();

  /** Deleting money from the record sits behind the Green PIN, so an unlocked
   *  session is required before the confirm dialog even opens. */
  const askToDelete = (txnId: string) => {
    if (isPinConfigured && !isUnlocked) {
      promptUnlock(() => setVoidTarget(txnId));
      return;
    }
    setVoidTarget(txnId);
  };

  if (isLoading || !person) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-5">
      <Link to="/bahi-khata" className="inline-flex items-center gap-1.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]">
        <ArrowLeft className="h-4 w-4" /> Back to Bahi Khata
      </Link>

      <Card className="p-5">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <Avatar name={person.name} color={person.color} size="lg" />
            <div>
              <h1 className="text-xl font-bold text-[var(--text-primary)]">{person.name}</h1>
              {person.relation && <p className="text-sm text-[var(--text-tertiary)]">{person.relation}</p>}
              <div className="mt-1 flex gap-3 text-xs text-[var(--text-secondary)]">
                {person.phone && (
                  <span className="flex items-center gap-1"><Phone className="h-3 w-3" /> {person.phone}</span>
                )}
                {person.email && (
                  <span className="flex items-center gap-1"><Mail className="h-3 w-3" /> {person.email}</span>
                )}
              </div>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {person.outstanding_receivable > 0 && (
              <Button size="sm" variant="secondary" onClick={() => setPayDirection("given")}>
                <IndianRupee className="h-4 w-4" /> Record payment
              </Button>
            )}
            {person.outstanding_payable > 0 && (
              <Button size="sm" variant="secondary" onClick={() => setPayDirection("borrowed")}>
                <IndianRupee className="h-4 w-4" /> Record repayment
              </Button>
            )}
            <Button size="sm" onClick={() => setAddOpen(true)}>
              <Plus className="h-4 w-4" /> Add
            </Button>
          </div>
        </div>

        <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat label="Total Given" value={person.total_given} />
          <Stat label="Total Received" value={person.total_received} />
          <Stat label="Outstanding" value={person.outstanding_receivable} accent="positive" />
          <Stat label="Transactions" value={person.entry_count} isCount />
        </div>

        {(person.outstanding_receivable > 0 || person.outstanding_payable > 0) && (
          <div className="mt-4 rounded-xl bg-[var(--bg-inset)] p-3.5 text-sm">
            Net balance:{" "}
            <CurrencyDisplay
              value={person.net_balance}
              clickToUnlock={false}
              className={person.net_balance >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}
            />
          </div>
        )}
      </Card>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Entries</h2>
        <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
          {person.entries.map((entry) => (
            <Link
              key={entry.id}
              to={`/bahi-khata/entries/${entry.id}`}
              className="flex items-center gap-3 p-4 hover:bg-[var(--bg-surface-hover)]"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-medium text-[var(--text-primary)]">{entry.purpose}</p>
                  <Badge variant={statusVariant(entry.status)}>{entry.status}</Badge>
                </div>
                <p className="text-xs text-[var(--text-tertiary)]">{formatDate(entry.entry_date, "short")}</p>
              </div>
              <CurrencyDisplay value={entry.outstanding} compact clickToUnlock={false} />
              {entry.outstanding > 0 && (
                <Button
                  size="sm"
                  variant="secondary"
                  // The row is a Link; don't let the button navigate.
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setRecordFor(entry);
                  }}
                >
                  <IndianRupee className="h-3.5 w-3.5" />
                  Record payment
                </Button>
              )}
            </Link>
          ))}
        </Card>
      </div>

      <div>
        <h2 className="mb-3 text-sm font-semibold text-[var(--text-primary)]">Ledger</h2>
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-[var(--border-subtle)] text-left text-xs text-[var(--text-tertiary)]">
                <tr>
                  <th className="px-4 py-2.5 font-medium">Date</th>
                  <th className="px-4 py-2.5 font-medium">Type</th>
                  <th className="px-4 py-2.5 font-medium">Description</th>
                  <th className="px-4 py-2.5 text-right font-medium">Amount</th>
                  <th className="px-4 py-2.5 text-right font-medium">Balance</th>
                  <th className="w-10 px-2 py-2.5" />
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {person.ledger.map((txn) => (
                  <tr key={txn.id} className={txn.is_voided ? "opacity-40" : ""}>
                    <td className="px-4 py-2.5 whitespace-nowrap text-[var(--text-secondary)]">{formatDate(txn.txn_date, "short")}</td>
                    <td className="px-4 py-2.5 capitalize text-[var(--text-secondary)]">{txn.txn_type.replace("_", " ")}</td>
                    <td className="px-4 py-2.5 text-[var(--text-secondary)]">{txn.purpose}</td>
                    <td className="px-4 py-2.5 text-right">
                      <CurrencyDisplay
                        value={txn.signed_amount}
                        compact
                        clickToUnlock={false}
                        className={txn.signed_amount >= 0 ? "text-[var(--positive)]" : "text-[var(--negative)]"}
                      />
                    </td>
                    <td className="px-4 py-2.5 text-right font-medium">
                      <CurrencyDisplay value={txn.balance_after} compact clickToUnlock={false} />
                    </td>
                    <td className="px-2 py-2.5 text-right">
                      {txn.is_voided ? (
                        <span
                          className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]"
                          title={txn.void_reason ?? undefined}
                        >
                          voided
                        </span>
                      ) : (
                        <button
                          type="button"
                          onClick={() => askToDelete(txn.id)}
                          className="rounded-lg p-1.5 text-[var(--text-tertiary)] hover:bg-[var(--bg-inset)] hover:text-[var(--negative)]"
                          title="Delete this transaction"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <CardContent className="p-0">
        <Button
          variant="ghost"
          className="text-[var(--text-tertiary)]"
          onClick={() => setArchiveConfirm(true)}
        >
          <Archive className="h-4 w-4" /> Remove from Bahi Khata
        </Button>
      </CardContent>

      {payDirection && (
        <RecordPersonPaymentDialog
          open
          onClose={() => setPayDirection(null)}
          personId={person.id}
          personName={person.name}
          direction={payDirection}
          outstanding={
            payDirection === "given"
              ? person.outstanding_receivable
              : person.outstanding_payable
          }
        />
      )}
      {recordFor && (
        <RecordTransactionDialog open onClose={() => setRecordFor(null)} entry={recordFor} />
      )}
      <AddEntryDialog open={addOpen} onClose={() => setAddOpen(false)} />

      <ConfirmDialog
        open={!!voidTarget}
        onClose={() => setVoidTarget(null)}
        title="Delete this transaction?"
        description="It stays in the history marked as voided, and the balance is corrected straight away."
        confirmLabel="Delete"
        variant="danger"
        onConfirm={async () => {
          if (!voidTarget) return;
          try {
            await voidTransaction.mutateAsync({
              txnId: voidTarget,
              reason: "Deleted from the ledger",
            });
            toast({ title: "Transaction deleted", variant: "success" });
            setVoidTarget(null);
          } catch (error) {
            toast({
              title: "Could not delete transaction",
              description: isApiError(error) ? error.message : undefined,
              variant: "error",
            });
          }
        }}
      />

      <ConfirmDialog
        open={archiveConfirm}
        onClose={() => setArchiveConfirm(false)}
        title={`Remove ${person.name}?`}
        description="This is only possible once every entry with them is fully settled."
        confirmLabel="Remove"
        variant="danger"
        onConfirm={async () => {
          try {
            await deletePerson.mutateAsync(person.id);
            toast({ title: "Person removed", variant: "success" });
            navigate("/bahi-khata");
          } catch (error) {
            toast({ title: "Could not remove person", description: isApiError(error) ? error.message : undefined, variant: "error" });
          }
        }}
      />
    </div>
  );
}

function Stat({ label, value, accent, isCount }: { label: string; value: number; accent?: "positive"; isCount?: boolean }) {
  return (
    <div>
      <p className="text-xs text-[var(--text-tertiary)]">{label}</p>
      {isCount ? (
        <p className="text-lg font-semibold text-[var(--text-primary)]">{value}</p>
      ) : (
        <CurrencyDisplay
          value={value}
          compact
          clickToUnlock={false}
          size="md"
          className={accent === "positive" ? "text-[var(--positive)] font-semibold" : "font-semibold"}
        />
      )}
    </div>
  );
}
