import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Notification } from "@/types";
import { useAuth } from "@/contexts/AuthContext";

export function useNotificationsUnreadCount() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: async () => {
      const { data } = await api.get<{ count: number }>("/notifications/unread-count");
      return data.count;
    },
    enabled: isAuthenticated,
    refetchInterval: 60_000,
  });
}

export function useNotifications(unreadOnly = false) {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["notifications", { unreadOnly }],
    queryFn: async () => {
      const { data } = await api.get<Notification[]>("/notifications", {
        params: { unread_only: unreadOnly },
      });
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useRefreshReminders() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ message: string }>("/notifications/refresh");
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkNotificationRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Notification>(`/notifications/${id}/read`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useMarkAllNotificationsRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ message: string }>("/notifications/read-all");
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}

export function useDismissNotification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete<{ message: string }>(`/notifications/${id}`);
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
}
