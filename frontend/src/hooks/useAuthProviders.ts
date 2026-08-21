import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useAuthProviders() {
  return useQuery({
    queryKey: ["auth-providers"],
    queryFn: async () => {
      const { data } = await api.get<{ google: boolean; password: boolean }>("/auth/providers");
      return data;
    },
    staleTime: Infinity,
  });
}
