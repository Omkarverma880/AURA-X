import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  LedgerAnalytics,
  LedgerEntryDetail,
  LedgerSummary,
  Page,
  Person,
  PersonDetail,
} from "@/types";

const KEYS = {
  people: (params?: object) => ["bahi-khata", "people", params] as const,
  person: (id: string) => ["bahi-khata", "person", id] as const,
  entries: (params?: object) => ["bahi-khata", "entries", params] as const,
  entry: (id: string) => ["bahi-khata", "entry", id] as const,
  summary: ["bahi-khata", "summary"] as const,
  analytics: (months?: number) => ["bahi-khata", "analytics", months] as const,
};

function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["bahi-khata"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

export function usePeople(params?: { search?: string; only_outstanding?: boolean; include_archived?: boolean }) {
  return useQuery({
    queryKey: KEYS.people(params),
    queryFn: async () => {
      const { data } = await api.get<Person[]>("/bahi-khata/people", { params });
      return data;
    },
  });
}

export function usePersonDetail(personId: string | undefined) {
  return useQuery({
    queryKey: KEYS.person(personId ?? ""),
    queryFn: async () => {
      const { data } = await api.get<PersonDetail>(`/bahi-khata/people/${personId}`);
      return data;
    },
    enabled: !!personId,
  });
}

export function useCreatePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; phone?: string; email?: string; relation?: string; notes?: string }) => {
      const { data } = await api.post<Person>("/bahi-khata/people", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdatePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<Person>(`/bahi-khata/people/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeletePerson() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/bahi-khata/people/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export interface EntryListParams {
  direction?: string;
  status?: string;
  person_id?: string;
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export function useEntries(params?: EntryListParams) {
  return useQuery({
    queryKey: KEYS.entries(params),
    queryFn: async () => {
      const { data } = await api.get<Page<LedgerEntryDetail>>("/bahi-khata/entries", { params });
      return data;
    },
  });
}

export function useEntryDetail(entryId: string | undefined) {
  return useQuery({
    queryKey: KEYS.entry(entryId ?? ""),
    queryFn: async () => {
      const { data } = await api.get<LedgerEntryDetail>(`/bahi-khata/entries/${entryId}`);
      return data;
    },
    enabled: !!entryId,
  });
}

export interface CreateEntryInput {
  person_id?: string;
  person_name?: string;
  direction: "given" | "borrowed";
  purpose: string;
  amount: number;
  entry_date?: string;
  due_date?: string | null;
  reminder_on?: string | null;
  method?: string;
  notes?: string;
}

export function useCreateEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateEntryInput) => {
      const { data } = await api.post<LedgerEntryDetail>("/bahi-khata/entries", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdateEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<LedgerEntryDetail>(`/bahi-khata/entries/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/bahi-khata/entries/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export interface AddTransactionInput {
  entryId: string;
  txn_type?: string;
  amount: number;
  txn_date?: string;
  method?: string;
  description?: string;
}

export function useAddTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ entryId, ...input }: AddTransactionInput) => {
      const { data } = await api.post<LedgerEntryDetail>(`/bahi-khata/entries/${entryId}/transactions`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useSettleEntry() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (entryId: string) => {
      const { data } = await api.post<LedgerEntryDetail>(`/bahi-khata/entries/${entryId}/settle`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useVoidTransaction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ txnId, reason }: { txnId: string; reason: string }) => {
      const { data } = await api.post(`/bahi-khata/transactions/${txnId}/void`, { reason });
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useLedgerSummary() {
  return useQuery({
    queryKey: KEYS.summary,
    queryFn: async () => {
      const { data } = await api.get<LedgerSummary>("/bahi-khata/summary");
      return data;
    },
  });
}

export function useLedgerAnalytics(months = 12) {
  return useQuery({
    queryKey: KEYS.analytics(months),
    queryFn: async () => {
      const { data } = await api.get<LedgerAnalytics>("/bahi-khata/analytics", { params: { months } });
      return data;
    },
  });
}
