import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Checklist, ChecklistDetail, ChecklistItem, LifeCategory, LifeGoal, LifeGoalDetail, Milestone } from "@/types";

function invalidateGoals(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["life-goals"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

function invalidateChecklists(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: ["checklists"] });
  void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  void queryClient.invalidateQueries({ queryKey: ["analytics"] });
}

// ── Life goals ───────────────────────────────────────────────────────

export function useLifeGoalCategories() {
  return useQuery({
    queryKey: ["life-goals", "categories"],
    queryFn: async () => {
      const { data } = await api.get<LifeCategory[]>("/goals/categories");
      return data;
    },
  });
}

export function useLifeGoals(params?: { status?: string; category_id?: string }) {
  return useQuery({
    queryKey: ["life-goals", "list", params],
    queryFn: async () => {
      const { data } = await api.get<LifeGoal[]>("/goals", { params });
      return data;
    },
  });
}

export function useLifeGoalDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["life-goals", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<LifeGoalDetail>(`/goals/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateLifeGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.post<LifeGoalDetail>("/goals", input);
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

export function useUpdateLifeGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<LifeGoalDetail>(`/goals/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

export function useDeleteLifeGoal() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/goals/${id}`);
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

export function useAddMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ goalId, title }: { goalId: string; title: string }) => {
      const { data } = await api.post<LifeGoalDetail>(`/goals/${goalId}/milestones`, { title });
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

export function useUpdateMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<Milestone>(`/goals/milestones/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

export function useDeleteMilestone() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/goals/milestones/${id}`);
      return data;
    },
    onSuccess: () => invalidateGoals(queryClient),
  });
}

// ── Checklists / trackers ───────────────────────────────────────────

export function useChecklists(params?: { tracker_type?: string; include_archived?: boolean }) {
  return useQuery({
    queryKey: ["checklists", "list", params],
    queryFn: async () => {
      const { data } = await api.get<Checklist[]>("/checklists", { params });
      return data;
    },
  });
}

export function useChecklistDetail(id: string | undefined) {
  return useQuery({
    queryKey: ["checklists", "detail", id],
    queryFn: async () => {
      const { data } = await api.get<ChecklistDetail>(`/checklists/${id}`);
      return data;
    },
    enabled: !!id,
  });
}

export function useCreateChecklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { title: string; tracker_type?: string; icon?: string; color?: string; target_count?: number; items?: string[] }) => {
      const { data } = await api.post<ChecklistDetail>("/checklists", input);
      return data;
    },
    onSuccess: () => invalidateChecklists(queryClient),
  });
}

export function useDeleteChecklist() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/checklists/${id}`);
      return data;
    },
    onSuccess: () => invalidateChecklists(queryClient),
  });
}

export function useAddChecklistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ checklistId, ...input }: { checklistId: string; name: string; location?: string }) => {
      const { data } = await api.post<ChecklistDetail>(`/checklists/${checklistId}/items`, input);
      return data;
    },
    onSuccess: () => invalidateChecklists(queryClient),
  });
}

export function useUpdateChecklistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, ...input }: { id: string; [key: string]: unknown }) => {
      const { data } = await api.patch<ChecklistItem>(`/checklists/items/${id}`, input);
      return data;
    },
    onSuccess: () => invalidateChecklists(queryClient),
  });
}

export function useDeleteChecklistItem() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/checklists/items/${id}`);
      return data;
    },
    onSuccess: () => invalidateChecklists(queryClient),
  });
}
