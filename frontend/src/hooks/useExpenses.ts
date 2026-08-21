import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type {
  Budget,
  Category,
  Expense,
  IncomeRecord,
  IncomeSource,
  MonthlySummary,
  Page,
  TrendPoint,
} from "@/types";

function invalidateAll(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["expenses"] });
  void queryClient.invalidateQueries({ queryKey: ["categories"] });
  void queryClient.invalidateQueries({ queryKey: ["budgets"] });
  void queryClient.invalidateQueries({ queryKey: ["income"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

// ── Categories ────────────────────────────────────────────────────────

export function useCategories(params?: { kind?: string; period?: string; include_archived?: boolean }) {
  return useQuery({
    queryKey: ["categories", params],
    queryFn: async () => {
      const { data } = await api.get<Category[]>("/categories", { params });
      return data;
    },
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; kind?: string; icon?: string; color?: string }) => {
      const { data } = await api.post<Category>("/categories", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/categories/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

// ── Expenses ─────────────────────────────────────────────────────────

export interface ExpenseListParams {
  period?: string;
  category_id?: string;
  search?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export function useExpenses(params?: ExpenseListParams) {
  return useQuery({
    queryKey: ["expenses", "list", params],
    queryFn: async () => {
      const { data } = await api.get<Page<Expense>>("/expenses", { params });
      return data;
    },
  });
}

export function useCreateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<Expense>("/expenses", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useUpdateExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<Expense>(`/expenses/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteExpense() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/expenses/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

// ── Monthly summary / trend ─────────────────────────────────────────

export function useMonthlySummary(period: string) {
  return useQuery({
    queryKey: ["expenses", "monthly-summary", period],
    queryFn: async () => {
      const { data } = await api.get<MonthlySummary>("/expenses/monthly-summary", { params: { period } });
      return data;
    },
  });
}

export function useExpenseTrend(months = 12, enabled = true) {
  return useQuery({
    queryKey: ["expenses", "trend", months],
    queryFn: async () => {
      const { data } = await api.get<TrendPoint[]>("/expenses/trend", { params: { months } });
      return data;
    },
    enabled,
  });
}

// ── Income ───────────────────────────────────────────────────────────

export function useIncomeSources() {
  return useQuery({
    queryKey: ["income", "sources"],
    queryFn: async () => {
      const { data } = await api.get<IncomeSource[]>("/income/sources");
      return data;
    },
  });
}

export function useCreateIncomeSource() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { name: string; income_type?: string; employer?: string }) => {
      const { data } = await api.post<IncomeSource>("/income/sources", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useIncome(params?: { period?: string; year?: number; page?: number; page_size?: number }) {
  return useQuery({
    queryKey: ["income", "list", params],
    queryFn: async () => {
      const { data } = await api.get<Page<IncomeRecord>>("/income", { params });
      return data;
    },
  });
}

export function useCreateIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<IncomeRecord>("/income", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteIncome() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/income/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

// ── Budgets ──────────────────────────────────────────────────────────

export function useBudgets(period: string) {
  return useQuery({
    queryKey: ["budgets", period],
    queryFn: async () => {
      const { data } = await api.get<Budget[]>("/budgets", { params: { period } });
      return data;
    },
  });
}

export function useUpsertBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { category_id: string; period_month: string; amount: number; notes?: string }) => {
      const { data } = await api.put<Budget>("/budgets", input);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}

export function useDeleteBudget() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/budgets/${id}`);
      return data;
    },
    onSuccess: () => invalidateAll(queryClient),
  });
}
