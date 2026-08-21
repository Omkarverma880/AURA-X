import { useEffect, useRef, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Dialog } from "@/components/ui/Dialog";
import { Button } from "@/components/ui/Button";
import { useFinancial } from "@/contexts/FinancialContext";
import { isApiError } from "@/lib/api";
import { Link, useNavigate } from "react-router-dom";

/**
 * The Green PIN unlock prompt.
 *
 * This dialog is presentation only - typing the right digits here means
 * nothing until the server accepts them (POST /security/financial/unlock).
 * A tampered frontend that "unlocks" without that call still gets 423s from
 * every protected endpoint.
 */
export function GreenPinModal() {
  const { isPromptOpen, closePrompt, unlock, isPinConfigured } = useFinancial();
  const [pin, setPin] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (isPromptOpen) {
      setPin("");
      setError(null);
      window.setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isPromptOpen]);

  const handleSubmit = async (value: string) => {
    if (value.length !== 4) return;
    setLoading(true);
    setError(null);
    try {
      await unlock(value);
    } catch (err) {
      if (isApiError(err)) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
      setPin("");
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (value: string) => {
    const digits = value.replace(/\D/g, "").slice(0, 4);
    setPin(digits);
    if (digits.length === 4) void handleSubmit(digits);
  };

  if (!isPinConfigured) {
    return (
      <Dialog open={isPromptOpen} onClose={closePrompt} title="Set up your Green PIN">
        <div className="flex flex-col items-center gap-4 py-2 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
            <ShieldCheck className="h-7 w-7 text-[var(--brand)]" />
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            Create a 4-digit Green PIN in Settings to keep your salary, expenses and investment
            figures hidden from prying eyes.
          </p>
          <Button
            onClick={() => {
              closePrompt();
              navigate("/settings/security");
            }}
          >
            Go to Settings
          </Button>
        </div>
      </Dialog>
    );
  }

  return (
    <Dialog open={isPromptOpen} onClose={closePrompt} title="Enter your Green PIN" mobileSheet={false}>
      <div className="flex flex-col items-center gap-5 py-2">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
          <ShieldCheck className="h-7 w-7 text-[var(--brand)]" />
        </div>
        <p className="text-center text-sm text-[var(--text-secondary)]">
          Unlock your financial data for {" "}
          <span className="font-medium text-[var(--text-primary)]">5 minutes</span>
        </p>

        <div className="relative">
          <input
            ref={inputRef}
            type="password"
            inputMode="numeric"
            autoComplete="off"
            maxLength={4}
            value={pin}
            disabled={loading}
            onChange={(e) => handleChange(e.target.value)}
            className="sr-only"
            aria-label="Green PIN"
          />
          <div
            className="flex gap-3"
            onClick={() => inputRef.current?.focus()}
            role="presentation"
          >
            {Array.from({ length: 4 }, (_, i) => (
              <div
                key={i}
                className="flex h-14 w-12 items-center justify-center rounded-xl border-2 text-xl font-semibold"
                style={{
                  borderColor: error ? "var(--negative)" : pin.length > i ? "var(--brand)" : "var(--border-default)",
                  background: "var(--bg-inset)",
                }}
              >
                {pin[i] ? "•" : ""}
              </div>
            ))}
          </div>
        </div>

        {error && <p className="text-sm text-[var(--negative)]">{error}</p>}
        {loading && <p className="text-sm text-[var(--text-tertiary)]">Verifying...</p>}

        <Link
          to="/settings/security"
          onClick={closePrompt}
          className="text-xs text-[var(--brand)] hover:underline"
        >
          Forgot your Green PIN?
        </Link>
      </div>
    </Dialog>
  );
}
