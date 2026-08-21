import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { api, isApiError } from "@/lib/api";

export function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("This verification link is missing its token.");
      return;
    }
    api
      .post("/auth/verify-email", { token })
      .then(() => setStatus("success"))
      .catch((error) => {
        setStatus("error");
        setMessage(isApiError(error) ? error.message : "This link is invalid or has expired.");
      });
  }, [token]);

  return (
    <AuthLayout title="E-mail verification">
      <div className="flex flex-col items-center gap-4 py-6 text-center">
        {status === "loading" && <Loader2 className="h-8 w-8 animate-spin text-[var(--brand)]" />}
        {status === "success" && (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--positive-soft)]">
              <CheckCircle2 className="h-7 w-7 text-[var(--positive)]" />
            </div>
            <p className="text-sm text-[var(--text-secondary)]">Your e-mail has been verified.</p>
          </>
        )}
        {status === "error" && (
          <>
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--negative-soft)]">
              <XCircle className="h-7 w-7 text-[var(--negative)]" />
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{message}</p>
          </>
        )}
        <Link to="/dashboard" className="text-sm font-medium text-[var(--brand)] hover:underline">
          Continue to Aura X
        </Link>
      </div>
    </AuthLayout>
  );
}
