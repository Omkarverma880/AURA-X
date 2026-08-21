import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, FieldHint } from "@/components/ui/Input";
import { api, isApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";

/** Passwordless sign-in with a phone number already linked in Settings. */
export function PhoneLoginPanel() {
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { loginWithPhone } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const requestOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post<{ message: string; debug_code: string | null }>(
        "/auth/phone/otp",
        { phone },
      );
      setDebugCode(data.debug_code);
      setStep("code");
      toast({ title: "Code sent", description: data.message, variant: "info" });
    } catch (err) {
      setError(isApiError(err) ? err.message : "Could not send the code.");
    } finally {
      setLoading(false);
    }
  };

  const verifyOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      await loginWithPhone(phone, code);
      navigate("/dashboard");
    } catch (err) {
      setError(isApiError(err) ? err.message : "That code is not valid.");
    } finally {
      setLoading(false);
    }
  };

  if (step === "phone") {
    return (
      <div className="space-y-4">
        <div>
          <Label htmlFor="phone">Phone number</Label>
          <Input
            id="phone"
            type="tel"
            placeholder="+919876543210"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
          />
          <FieldHint>Include the country code, e.g. +91 for India.</FieldHint>
          <FieldError>{error ?? undefined}</FieldError>
        </div>
        <Button className="w-full" onClick={requestOtp} loading={loading} disabled={!phone}>
          <Smartphone className="h-4 w-4" /> Send code
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="otp">Enter the 6-digit code</Label>
        <Input
          id="otp"
          inputMode="numeric"
          maxLength={6}
          placeholder="000000"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
          className="tracking-[0.4em] text-center"
        />
        {debugCode && (
          <FieldHint>
            Development mode - your code is <span className="font-mono font-semibold">{debugCode}</span>
          </FieldHint>
        )}
        <FieldError>{error ?? undefined}</FieldError>
      </div>
      <Button className="w-full" onClick={verifyOtp} loading={loading} disabled={code.length !== 6}>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />} Verify &amp; sign in
      </Button>
      <button
        type="button"
        onClick={() => { setStep("phone"); setCode(""); setError(null); }}
        className="w-full text-center text-xs text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
      >
        Use a different number
      </button>
    </div>
  );
}
