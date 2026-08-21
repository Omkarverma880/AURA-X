import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AnalyticsOverview, DashboardData } from "@/types";
import { useAuth } from "@/contexts/AuthContext";

export function useDashboard() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: async () => {
      const { data } = await api.get<DashboardData>("/dashboard");
      return data;
    },
    enabled: isAuthenticated,
    refetchInterval: 60_000,
  });
}

export function useAnalyticsOverview() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["analytics", "overview"],
    queryFn: async () => {
      const { data } = await api.get<AnalyticsOverview>("/analytics");
      return data;
    },
    enabled: isAuthenticated,
  });
}
