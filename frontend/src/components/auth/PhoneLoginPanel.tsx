import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Smartphone } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { Label, FieldError, FieldHint, Input } from "@/components/ui/Input";
import { PhoneInput } from "@/components/shared/PhoneInput";
import { api, isApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/contexts/ToastContext";

/** Phone-first sign-in: entering a number always gets a code, and verifying
 * it either signs in the account already holding that number or creates a
 * new one on the spot - the same model Google sign-in uses for e-mail. */
export function PhoneLoginPanel() {
  const [step, setStep] = useState<"phone" | "code">("phone");
  const [phone, setPhone] = useState("");
  const [code, setCode] = useState("");
  const [fullName, setFullName] = useState("");
  const [debugCode, setDebugCode] = useState<string | null>(null);
  const [channel, setChannel] = useState<string>("none");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { loginWithPhone } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const requestOtp = async () => {
    setError(null);
    setLoading(true);
    try {
      const { data } = await api.post<{ message: string; channel: string; debug_code: string | null }>(
        "/auth/phone/otp",
        { phone },
      );
      setDebugCode(data.debug_code);
      setChannel(data.channel);
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
      await loginWithPhone(phone, code, fullName);
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
          <PhoneInput id="phone" value={phone} onChange={setPhone} autoFocus />
          <FieldHint>New here? We'll set up your account automatically. Your number is only used for sign-in and is never shared.</FieldHint>
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
        <FieldHint>{codeSentHint(channel, phone)}</FieldHint>
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

      <div>
        <Label htmlFor="full_name">
          Your name <span className="font-normal text-[var(--text-tertiary)]">(only needed for a new number)</span>
        </Label>
        <Input id="full_name" value={fullName} onChange={(e) => setFullName(e.target.value)} />
      </div>

      <Button className="w-full" onClick={verifyOtp} loading={loading} disabled={code.length !== 6}>
        {loading && <Loader2 className="h-4 w-4 animate-spin" />} Verify &amp; continue
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

/** Tells the user which app to go looking in - a code that arrived on
 * WhatsApp is easy to miss while staring at the SMS inbox. */
function codeSentHint(channel: string, phone: string): string {
  if (channel === "whatsapp") return `Sent on WhatsApp to ${phone}.`;
  if (channel === "sms") return `Sent by SMS to ${phone}.`;
  return `Sent to ${phone}.`;
}
