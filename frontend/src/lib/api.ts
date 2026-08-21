import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";

/**
 * The single HTTP client every hook goes through.
 *
 * Auth lives entirely in HttpOnly cookies (`withCredentials: true`), so this
 * file never touches an access or refresh token directly - it only reads the
 * CSRF cookie, which is deliberately the one auth cookie JavaScript *can*
 * see, and echoes it back in a header on state-changing requests. That's the
 * double-submit check the backend verifies in app/core/deps.py.
 */

export const API_BASE = "/api/v1";

export const api = axios.create({
  baseURL: API_BASE,
  withCredentials: true,
});

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

const SAFE_METHODS = new Set(["get", "head", "options"]);

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const method = (config.method ?? "get").toLowerCase();
  if (!SAFE_METHODS.has(method)) {
    const csrf = readCookie("bk_csrf");
    if (csrf) {
      config.headers.set("X-CSRF-Token", csrf);
    }
  }
  return config;
});

/** Shape of the error envelope every failing endpoint returns. */
export interface ApiErrorBody {
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
}

export class ApiError extends Error {
  code: string;
  status: number;
  details?: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function toApiError(error: AxiosError<ApiErrorBody>): ApiError {
  const status = error.response?.status ?? 0;
  const body = error.response?.data?.error;
  if (body) {
    return new ApiError(status, body.code, body.message, body.details);
  }
  if (error.code === "ERR_NETWORK") {
    return new ApiError(0, "network_error", "Could not reach the server. Check your connection.");
  }
  return new ApiError(status, "unknown_error", error.message || "Something went wrong.");
}

let refreshPromise: Promise<void> | null = null;

async function refreshSession(): Promise<void> {
  refreshPromise ??= axios
    .post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
    .then(() => undefined)
    .finally(() => {
      refreshPromise = null;
    });
  return refreshPromise;
}

/** Paths that must never trigger a refresh-and-retry loop. */
const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh", "/auth/logout"];

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError<ApiErrorBody>) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retried?: boolean }) | undefined;
    const isAuthEndpoint = original?.url ? AUTH_ENDPOINTS.some((p) => original.url!.includes(p)) : false;

    if (error.response?.status === 401 && original && !original._retried && !isAuthEndpoint) {
      original._retried = true;
      try {
        await refreshSession();
        return api(original);
      } catch {
        // Refresh failed too - fall through to the normal error path so the
        // caller (usually the auth context) can redirect to /login.
      }
    }

    return Promise.reject(toApiError(error));
  },
);

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError;
}
