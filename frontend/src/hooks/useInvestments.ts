import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { HoldingDetail, InvestmentAccount, InvestmentGoal, Holding, PortfolioSummary } from "@/types";

function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["investments"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

export function useHoldings(params?: { asset_type?: string; account_id?: string; include_inactive?: boolean }) {
  return useQuery({
    queryKey: ["investments", "holdings", params],
    queryFn: async () => {
      const { data } = await api.get<Holding[]>("/investments", { params });
      return data;
    },
  });
}

export function useHoldingDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["investments", "holding", id],
    queryFn: async () => {
      const { data } = await api.get<HoldingDetail>(`/investments/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function usePortfolioSummary() {
  return useQuery({
    queryKey: ["investments", "summary"],
    queryFn: async () => {
      const { data } = await api.get<PortfolioSummary>("/investments/summary");
      return data;
    },
  });
}

export function useInvestmentAccounts() {
  return useQuery({
    queryKey: ["investments", "accounts"],
    queryFn: async () => {
      const { data } = await api.get<InvestmentAccount[]>("/investments/accounts");
      return data;
    },
  });
}

export function useCreateAccount() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; broker?: string; account_number?: string }) => {
      const { data } = await api.post<InvestmentAccount>("/investments/accounts", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useCreateHolding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<HoldingDetail>("/investments", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdateHolding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<HoldingDetail>(`/investments/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteHolding() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/investments/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useAddInvestmentTxn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ holdingId, ...input }: { holdingId: string; [key: string]: unknown }) => {
      const { data } = await api.post<HoldingDetail>(`/investments/${holdingId}/transactions`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteInvestmentTxn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (txnId: string) => {
      const { data } = await api.delete(`/investments/transactions/${txnId}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

// ── Investment goal planner ─────────────────────────────────────────

export function useInvestmentGoals() {
  return useQuery({
    queryKey: ["investments", "goals"],
    queryFn: async () => {
      const { data } = await api.get<InvestmentGoal[]>("/investment-goals");
      return data;
    },
  });
}

export function useCreateInvestmentGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<InvestmentGoal>("/investment-goals", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdateInvestmentGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<InvestmentGoal>(`/investment-goals/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteInvestmentGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/investment-goals/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}
