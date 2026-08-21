import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search, User, BookOpenText, Receipt, TrendingUp, Target, ListChecks, Images } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { api } from "@/lib/api";
import type { SearchResult } from "@/types";

const TYPE_META: Record<string, { icon: typeof User; label: string; route: (id: string) => string }> = {
  person: { icon: User, label: "Person", route: (id) => `/bahi-khata/people/${id}` },
  ledger_entry: { icon: BookOpenText, label: "Bahi Khata entry", route: () => `/bahi-khata` },
  expense: { icon: Receipt, label: "Expense", route: () => `/expenses` },
  investment: { icon: TrendingUp, label: "Investment", route: (id) => `/investments/${id}` },
  life_goal: { icon: Target, label: "Life goal", route: (id) => `/goals/${id}` },
  checklist: { icon: ListChecks, label: "Tracker", route: (id) => `/goals/checklists/${id}` },
  album: { icon: Images, label: "Album", route: (id) => `/memories/${id}` },
};

export function SearchModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    if (!open) setQuery("");
  }, [open]);

  const { data, isFetching } = useQuery({
    queryKey: ["search", query],
    queryFn: async () => {
      const { data } = await api.get<{ query: string; results: SearchResult[] }>("/search", {
        params: { q: query },
      });
      return data.results;
    },
    enabled: open && query.trim().length >= 2,
  });

  const handleSelect = (result: SearchResult) => {
    const meta = TYPE_META[result.type];
    onClose();
    if (meta) navigate(meta.route(result.id));
  };

  return (
    <Dialog open={open} onClose={onClose} mobileSheet={false} className="max-w-lg">
      <div className="flex items-center gap-2 rounded-xl border border-[var(--border-default)] bg-[var(--bg-inset)] px-3">
        <Search className="h-4 w-4 text-[var(--text-tertiary)]" />
        <input
          autoFocus
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search people, expenses, investments, goals..."
          className="h-11 flex-1 bg-transparent text-sm text-[var(--text-primary)] outline-none placeholder:text-[var(--text-tertiary)]"
        />
      </div>

      <div className="mt-3 max-h-80 space-y-1 overflow-y-auto">
        {isFetching && <p className="px-2 py-6 text-center text-sm text-[var(--text-tertiary)]">Searching...</p>}
        {!isFetching && query.trim().length >= 2 && data?.length === 0 && (
          <p className="px-2 py-6 text-center text-sm text-[var(--text-tertiary)]">No results for "{query}"</p>
        )}
        {data?.map((result) => {
          const meta = TYPE_META[result.type];
          const Icon = meta?.icon ?? Search;
          return (
            <button
              key={`${result.type}-${result.id}`}
              onClick={() => handleSelect(result)}
              className="flex w-full items-center gap-3 rounded-lg px-2.5 py-2.5 text-left hover:bg-[var(--bg-inset)]"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--brand-soft)]">
                <Icon className="h-4 w-4 text-[var(--brand)]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[var(--text-primary)]">{result.title}</p>
                <p className="truncate text-xs text-[var(--text-tertiary)]">
                  {meta?.label ?? result.type}
                  {result.subtitle ? ` · ${result.subtitle}` : ""}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </Dialog>
  );
}
