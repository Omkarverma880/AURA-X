import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useQueryClient } from "@tanstack/react-query";
import { api, isApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import type { FinancialStatus } from "@/types";

/** Top-level query keys whose data the backend withholds or nulls out while
 * financial data is locked - these must be refetched the instant lock state
 * flips in either direction, or the UI shows stale masked/unmasked figures. */
const FINANCIAL_QUERY_KEYS = ["dashboard", "analytics", "income", "investments", "budgets", "expenses"];

/**
 * Orchestrates the Green PIN unlock UI.
 *
 * The server is the real gate (app/core/deps.py::require_finance_unlock) -
 * this context only tracks presentation state (a live countdown, whether the
 * unlock dialog is open) and refetches the authoritative status after every
 * unlock/lock so the countdown can never drift from what the backend enforces.
 */

interface FinancialContextValue {
  status: FinancialStatus | null;
  secondsRemaining: number;
  isUnlocked: boolean;
  isPinConfigured: boolean;
  promptUnlock: (onSuccess?: () => void) => void;
  closePrompt: () => void;
  isPromptOpen: boolean;
  unlockCallback: (() => void) | undefined;
  unlock: (pin: string) => Promise<void>;
  lock: () => Promise<void>;
  refreshStatus: () => Promise<void>;
}

const FinancialContext = createContext<FinancialContextValue | null>(null);

export function FinancialProvider({ children }: { children: ReactNode }) {
  const { financial, setFinancial, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [countdown, setCountdown] = useState(financial?.seconds_remaining ?? 0);
  const [isPromptOpen, setPromptOpen] = useState(false);
  const successRef = useRef<(() => void) | undefined>(undefined);

  const invalidateFinancialQueries = useCallback(() => {
    for (const key of FINANCIAL_QUERY_KEYS) {
      void queryClient.invalidateQueries({ queryKey: [key] });
    }
  }, [queryClient]);

  useEffect(() => {
    setCountdown(financial?.seconds_remaining ?? 0);
  }, [financial]);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setInterval(() => {
      setCountdown((value) => Math.max(value - 1, 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [countdown > 0]); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshStatus = useCallback(async () => {
    if (!isAuthenticated) return;
    try {
      const { data } = await api.get<FinancialStatus>("/security/financial/status");
      setFinancial(data);
    } catch (error) {
      if (!isApiError(error)) throw error;
    }
  }, [isAuthenticated, setFinancial]);

  // Relock automatically the moment the countdown reaches zero, then confirm
  // with the server (clock skew or a slow tab could otherwise show "unlocked"
  // a few seconds past the real expiry) and remask every dependent screen.
  useEffect(() => {
    if (countdown === 0 && financial?.unlocked) {
      void refreshStatus().then(invalidateFinancialQueries);
    }
  }, [countdown, financial?.unlocked, refreshStatus, invalidateFinancialQueries]);

  const promptUnlock = useCallback((onSuccess?: () => void) => {
    successRef.current = onSuccess;
    setPromptOpen(true);
  }, []);

  const closePrompt = useCallback(() => {
    setPromptOpen(false);
    successRef.current = undefined;
  }, []);

  const unlock = useCallback(
    async (pin: string) => {
      const { data } = await api.post<FinancialStatus>("/security/financial/unlock", { pin });
      setFinancial(data);
      invalidateFinancialQueries();
      setPromptOpen(false);
      successRef.current?.();
      successRef.current = undefined;
    },
    [setFinancial, invalidateFinancialQueries],
  );

  const lock = useCallback(async () => {
    const { data } = await api.post<FinancialStatus>("/security/financial/lock");
    setFinancial(data);
    invalidateFinancialQueries();
  }, [setFinancial, invalidateFinancialQueries]);

  const value = useMemo<FinancialContextValue>(
    () => ({
      status: financial,
      secondsRemaining: countdown,
      isUnlocked: financial?.unlocked ?? false,
      isPinConfigured: financial?.pin_configured ?? false,
      promptUnlock,
      closePrompt,
      isPromptOpen,
      unlockCallback: successRef.current,
      unlock,
      lock,
      refreshStatus,
    }),
    [financial, countdown, promptUnlock, closePrompt, isPromptOpen, unlock, lock, refreshStatus],
  );

  return <FinancialContext.Provider value={value}>{children}</FinancialContext.Provider>;
}

export function useFinancial(): FinancialContextValue {
  const ctx = useContext(FinancialContext);
  if (!ctx) throw new Error("useFinancial must be used within FinancialProvider");
  return ctx;
}

export function formatCountdown(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}
