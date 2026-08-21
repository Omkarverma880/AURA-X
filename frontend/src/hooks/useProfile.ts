import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { AuthResponse, SessionInfo, User } from "@/types";
import { useAuth } from "@/contexts/AuthContext";

export function useSessions() {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: ["sessions"],
    queryFn: async () => {
      const { data } = await api.get<SessionInfo[]>("/security/sessions");
      return data;
    },
    enabled: isAuthenticated,
  });
}

export function useUpdateProfile() {
  const { setUser } = useAuth();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: Record<string, unknown>) => {
      const { data } = await api.patch<User>("/users/me", input);
      return data;
    },
    onSuccess: (user) => {
      setUser(user);
      void queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useUploadAvatar() {
  const { setUser } = useAuth();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const { data } = await api.post<User>("/users/me/avatar", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return data;
    },
    onSuccess: (user) => setUser(user),
  });
}

export function useChangePassword() {
  return useMutation({
    mutationFn: async (input: { current_password: string; new_password: string }) => {
      const { data } = await api.post<{ message: string }>("/auth/change-password", input);
      return data;
    },
  });
}

export function useRequestPhoneLinkOtp() {
  return useMutation({
    mutationFn: async (phone: string) => {
      const { data } = await api.post<{ message: string; expires_in_minutes: number; channel: string; debug_code: string | null }>(
        "/users/me/phone/otp",
        { phone },
      );
      return data;
    },
  });
}

export function useConfirmPhoneLink() {
  const { setUser } = useAuth();
  return useMutation({
    mutationFn: async (code: string) => {
      const { data } = await api.post<User>("/users/me/phone/verify", { code });
      return data;
    },
    onSuccess: (user) => setUser(user),
  });
}

export function useUnlinkPhone() {
  const { setUser } = useAuth();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.delete<User>("/users/me/phone");
      return data;
    },
    onSuccess: (user) => setUser(user),
  });
}

export function useDeleteAccount() {
  return useMutation({
    mutationFn: async (confirm: string) => {
      const { data } = await api.delete<{ message: string }>("/users/me", { params: { confirm } });
      return data;
    },
  });
}

// ── Green PIN ────────────────────────────────────────────────────────

export function useSetGreenPin() {
  const { setFinancial } = useAuth();
  return useMutation({
    mutationFn: async (input: { new_pin: string; current_pin?: string }) => {
      const { data } = await api.post<{ message: string }>("/security/green-pin", input);
      return data;
    },
    onSuccess: async () => {
      const { data } = await api.get("/security/financial/status");
      setFinancial(data);
    },
  });
}

export function useForgotGreenPin() {
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post<{ message: string }>("/security/green-pin/forgot");
      return data;
    },
  });
}

export function useUpdateSecurityPreferences() {
  const { setFinancial } = useAuth();
  return useMutation({
    mutationFn: async (input: { unlock_minutes?: number; mask_ledger_amounts?: boolean }) => {
      const { data } = await api.patch("/security/preferences", input);
      return data;
    },
    onSuccess: (data) => setFinancial(data as never),
  });
}

// ── Sessions ─────────────────────────────────────────────────────────

export function useRevokeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.delete(`/security/sessions/${id}`);
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export function useRevokeAllSessions() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/security/sessions/revoke-all");
      return data;
    },
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["sessions"] }),
  });
}

export type { AuthResponse };
