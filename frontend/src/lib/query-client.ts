import { QueryClient } from "@tanstack/react-query";
import { isApiError } from "@/lib/api";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      gcTime: 5 * 60_000,
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => {
        // Auth/permission/validation failures will never succeed on retry.
        if (isApiError(error) && [400, 401, 403, 404, 409, 422, 423].includes(error.status)) {
          return false;
        }
        return failureCount < 2;
      },
    },
    mutations: {
      retry: false,
    },
  },
});
