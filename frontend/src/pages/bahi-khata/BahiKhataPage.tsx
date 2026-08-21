import { useState } from "react";
import { Link } from "react-router-dom";
import { Plus, Search, HandCoins, Wallet, TrendingDown, TrendingUp, BookOpenText, IndianRupee } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Badge, statusVariant } from "@/components/ui/Badge";
import { Avatar } from "@/components/ui/Avatar";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonList } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/shared/StatCard";
import { CurrencyDisplay } from "@/components/shared/CurrencyDisplay";
import { AddEntryDialog } from "@/components/bahi-khata/AddEntryDialog";
import { RecordTransactionDialog } from "@/components/bahi-khata/RecordTransactionDialog";
import { RecordPersonPaymentDialog } from "@/components/bahi-khata/RecordPersonPaymentDialog";
import { useEntries, useLedgerSummary, usePeople } from "@/hooks/useBahiKhata";
import { formatDate } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { LedgerEntry, Person } from "@/types";

type Tab = "people" | "entries";

export function BahiKhataPage() {
  const [tab, setTab] = useState<Tab>("people");
  const [search, setSearch] = useState("");
  const [direction, setDirection] = useState<"" | "given" | "borrowed">("");
  const [addOpen, setAddOpen] = useState(false);
  const [addDirection, setAddDirection] = useState<"given" | "borrowed">("given");
  // Recording a repayment used to live only on the entry detail page, three
  // clicks from here - so money coming back in was easy to miss entirely.
  const [recordFor, setRecordFor] = useState<LedgerEntry | null>(null);
  // Settling against a person, not a loan - the way a khata is actually kept.
  const [payPerson, setPayPerson] = useState<{ person: Person; direction: "given" | "borrowed" } | null>(null);

  const { data: summary } = useLedgerSummary();
  const { data: people, isLoading: peopleLoading } = usePeople({ search: search || undefined });
  const { data: entries, isLoading: entriesLoading } = useEntries({
    search: search || undefined,
    direction: direction || undefined,
    sort: "recent",
    page_size: 50,
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-[var(--text-primary)]">Bahi Khata</h1>
          <p className="text-sm text-[var(--text-secondary)]">Kya diya, kya liya, kon kitna baaki hai.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => { setAddDirection("borrowed"); setAddOpen(true); }}>
            <TrendingDown className="h-4 w-4" /> Borrowed
          </Button>
          <Button onClick={() => { setAddDirection("given"); setAddOpen(true); }}>
            <Plus className="h-4 w-4" /> Money Given
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <StatCard
          label="Money Given"
          icon={HandCoins}
          value={<CurrencyDisplay value={summary?.total_given} compact size="lg" clickToUnlock={false} />}
        />
        <StatCard
          label="To Receive"
          icon={TrendingUp}
          value={<CurrencyDisplay value={summary?.outstanding_receivable} compact size="lg" clickToUnlock={false} />}
        />
        <StatCard
          label="Money Borrowed"
          icon={Wallet}
          value={<CurrencyDisplay value={summary?.total_borrowed} compact size="lg" clickToUnlock={false} />}
        />
        <StatCard
          label="To Pay"
          icon={TrendingDown}
          value={<CurrencyDisplay value={summary?.outstanding_payable} compact size="lg" clickToUnlock={false} />}
        />
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl bg-[var(--bg-inset)] p-1 text-sm">
          {(["people", "entries"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={cn(
                "rounded-lg px-4 py-2 font-medium capitalize transition-colors",
                tab === t ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-soft" : "text-[var(--text-tertiary)]",
              )}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="relative ml-auto w-full max-w-xs">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[var(--text-tertiary)]" />
          <Input placeholder="Search..." className="pl-9" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>

        {tab === "entries" && (
          <Select value={direction} onChange={setDirection} />
        )}
      </div>

      {tab === "people" ? (
        <PeopleGrid loading={peopleLoading} people={people} onPay={(person, direction) => setPayPerson({ person, direction })} />
      ) : (
        <EntriesList loading={entriesLoading} entries={entries?.items} onRecord={setRecordFor} />
      )}

      <AddEntryDialog open={addOpen} onClose={() => setAddOpen(false)} defaultDirection={addDirection} />
      {payPerson && (
        <RecordPersonPaymentDialog
          open
          onClose={() => setPayPerson(null)}
          personId={payPerson.person.id}
          personName={payPerson.person.name}
          direction={payPerson.direction}
          outstanding={
            payPerson.direction === "given"
              ? payPerson.person.outstanding_receivable
              : payPerson.person.outstanding_payable
          }
        />
      )}
      {recordFor && (
        <RecordTransactionDialog
          open
          onClose={() => setRecordFor(null)}
          entry={recordFor}
        />
      )}
    </div>
  );
}

function Select({ value, onChange }: { value: string; onChange: (v: "" | "given" | "borrowed") => void }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as "" | "given" | "borrowed")}
      className="h-11 rounded-xl border border-[var(--border-default)] bg-[var(--bg-surface)] px-3 text-sm text-[var(--text-primary)]"
    >
      <option value="">All directions</option>
      <option value="given">Given</option>
      <option value="borrowed">Borrowed</option>
    </select>
  );
}

function PeopleGrid({
  loading,
  people,
  onPay,
}: {
  loading: boolean;
  people?: Person[];
  onPay: (person: Person, direction: "given" | "borrowed") => void;
}) {
  if (loading) {
    return (
      <Card>
        <SkeletonList rows={5} />
      </Card>
    );
  }

  if (!people?.length) {
    return (
      <Card>
        <EmptyState
          icon={BookOpenText}
          title="Your ledger is empty"
          description="Add the first person you have lent to or borrowed from."
        />
      </Card>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {people.map((person) => (
        <Link key={person.id} to={`/bahi-khata/people/${person.id}`}>
          <Card className="h-full p-4 transition-transform hover:-translate-y-0.5 hover:shadow-elevated">
            <div className="flex items-start gap-3">
              <Avatar name={person.name} color={person.color} />
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-[var(--text-primary)]">{person.name}</p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  {person.entry_count} {person.entry_count === 1 ? "entry" : "entries"} · {person.active_count} active
                </p>
              </div>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-2 text-sm">
              {person.outstanding_receivable > 0 && (
                <div>
                  <p className="text-xs text-[var(--text-tertiary)]">To receive</p>
                  <CurrencyDisplay value={person.outstanding_receivable} compact clickToUnlock={false} className="text-[var(--positive)]" />
                </div>
              )}
              {person.outstanding_payable > 0 && (
                <div>
                  <p className="text-xs text-[var(--text-tertiary)]">To pay</p>
                  <CurrencyDisplay value={person.outstanding_payable} compact clickToUnlock={false} className="text-[var(--negative)]" />
                </div>
              )}
              {person.outstanding_receivable === 0 && person.outstanding_payable === 0 && (
                <Badge variant="positive">All settled</Badge>
              )}
            </div>
            {(person.outstanding_receivable > 0 || person.outstanding_payable > 0) && (
              <div className="mt-3 flex gap-2">
                {person.outstanding_receivable > 0 && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="flex-1"
                    // The whole card is a Link; keep the button from navigating.
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onPay(person, "given");
                    }}
                  >
                    <IndianRupee className="h-3.5 w-3.5" /> Record payment
                  </Button>
                )}
                {person.outstanding_payable > 0 && (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="flex-1"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      onPay(person, "borrowed");
                    }}
                  >
                    <IndianRupee className="h-3.5 w-3.5" /> Record payment
                  </Button>
                )}
              </div>
            )}
          </Card>
        </Link>
      ))}
    </div>
  );
}

function EntriesList({
  loading,
  entries,
  onRecord,
}: {
  loading: boolean;
  entries?: LedgerEntry[];
  onRecord: (entry: LedgerEntry) => void;
}) {
  if (loading) {
    return (
      <Card>
        <SkeletonList rows={6} />
      </Card>
    );
  }

  if (!entries?.length) {
    return (
      <Card>
        <EmptyState icon={BookOpenText} title="No entries yet" description="Entries you add will show up here." />
      </Card>
    );
  }

  return (
    <Card className="divide-y divide-[var(--border-subtle)] overflow-hidden">
      {entries.map((entry) => (
        <Link
          key={entry.id}
          to={`/bahi-khata/entries/${entry.id}`}
          className="flex items-center gap-4 p-4 transition-colors hover:bg-[var(--bg-surface-hover)]"
        >
          <Avatar name={entry.person_name ?? "?"} size="sm" />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-medium text-[var(--text-primary)]">{entry.person_name}</p>
              <Badge variant={statusVariant(entry.status)}>{entry.status}</Badge>
            </div>
            <p className="truncate text-xs text-[var(--text-tertiary)]">
              {entry.purpose} · {formatDate(entry.entry_date, "short")}
              {entry.due_date ? ` · due ${formatDate(entry.due_date, "short")}` : ""}
            </p>
            {entry.status === "partial" && (
              <ProgressBar value={entry.progress_percent} className="mt-1.5 max-w-40" variant="brand" />
            )}
          </div>
          <div className="text-right">
            <CurrencyDisplay
              value={entry.outstanding}
              compact
              clickToUnlock={false}
              className={entry.direction === "given" ? "text-[var(--positive)]" : "text-[var(--negative)]"}
              size="sm"
            />
            <p className="text-[10px] uppercase tracking-wide text-[var(--text-tertiary)]">
              {entry.direction === "given" ? "receivable" : "payable"}
            </p>
          </div>
          {entry.outstanding > 0 && (
            <Button
              size="sm"
              variant="secondary"
              // The row is a Link, so keep the click from navigating away.
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onRecord(entry);
              }}
            >
              <IndianRupee className="h-3.5 w-3.5" />
              Record payment
            </Button>
          )}
        </Link>
      ))}
    </Card>
  );
}
