import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { KeyRound, ShieldCheck, Smartphone, Monitor, LogOut } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { Badge } from "@/components/ui/Badge";
import { useFinancial } from "@/contexts/FinancialContext";
import { useToast } from "@/contexts/ToastContext";
import {
  useChangePassword,
  useForgotGreenPin,
  useRevokeAllSessions,
  useRevokeSession,
  useSessions,
  useSetGreenPin,
} from "@/hooks/useProfile";
import { isApiError } from "@/lib/api";
import { formatDateTime } from "@/lib/format";

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Enter your current password."),
    new_password: z.string().min(8, "At least 8 characters."),
    confirm: z.string(),
  })
  .refine((v) => v.new_password === v.confirm, { message: "Passwords do not match.", path: ["confirm"] });
type PasswordForm = z.infer<typeof passwordSchema>;

export function SecuritySettingsPage() {
  return (
    <div className="space-y-5">
      <ChangePasswordCard />
      <GreenPinCard />
      <SessionsCard />
    </div>
  );
}

function ChangePasswordCard() {
  const { toast } = useToast();
  const changePassword = useChangePassword();
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<PasswordForm>({
    resolver: zodResolver(passwordSchema),
  });

  const onSubmit = async (values: PasswordForm) => {
    try {
      await changePassword.mutateAsync(values);
      toast({ title: "Password updated. Other devices signed out.", variant: "success" });
      reset();
    } catch (error) {
      toast({ title: "Could not change password", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><KeyRound className="h-4 w-4" /> Password</CardTitle>
        <CardDescription>Changing your password signs out every other device.</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="current_password">Current password</Label>
            <PasswordInput id="current_password" autoComplete="current-password" {...register("current_password")} error={!!errors.current_password} />
            <FieldError>{errors.current_password?.message}</FieldError>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="new_password">New password</Label>
              <PasswordInput id="new_password" autoComplete="new-password" {...register("new_password")} error={!!errors.new_password} />
              <FieldError>{errors.new_password?.message}</FieldError>
            </div>
            <div>
              <Label htmlFor="confirm">Confirm</Label>
              <PasswordInput id="confirm" autoComplete="new-password" {...register("confirm")} error={!!errors.confirm} />
              <FieldError>{errors.confirm?.message}</FieldError>
            </div>
          </div>
          <Button type="submit" loading={isSubmitting}>Update password</Button>
        </form>
      </CardContent>
    </Card>
  );
}

function GreenPinCard() {
  const { toast } = useToast();
  const { status, lock, isUnlocked } = useFinancial();
  const setPin = useSetGreenPin();
  const forgotPin = useForgotGreenPin();
  const [currentPin, setCurrentPin] = useState("");
  const [newPin, setNewPin] = useState("");

  const save = async () => {
    try {
      await setPin.mutateAsync({ new_pin: newPin, current_pin: status?.pin_configured ? currentPin : undefined });
      toast({ title: status?.pin_configured ? "Green PIN changed" : "Green PIN created", variant: "success" });
      setCurrentPin("");
      setNewPin("");
    } catch (error) {
      toast({ title: "Could not save Green PIN", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  const requestReset = async () => {
    try {
      const result = await forgotPin.mutateAsync();
      toast({ title: "Reset link sent", description: result.message, variant: "info" });
    } catch (error) {
      toast({ title: "Could not send reset link", description: isApiError(error) ? error.message : undefined, variant: "error" });
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><ShieldCheck className="h-4 w-4" /> Green PIN</CardTitle>
        <CardDescription>
          Protects salary, expenses and investment figures. Not the same as your login password.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status?.pin_configured && (
          <div className="flex items-center justify-between rounded-xl bg-[var(--bg-inset)] p-3.5 text-sm">
            <span className="text-[var(--text-secondary)]">
              Financial data is currently {isUnlocked ? "unlocked" : "locked"}.
            </span>
            {isUnlocked && (
              <Button size="sm" variant="secondary" onClick={() => lock()}>Lock now</Button>
            )}
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {status?.pin_configured && (
            <div>
              <Label htmlFor="current_pin">Current PIN</Label>
              <Input
                id="current_pin"
                inputMode="numeric"
                maxLength={4}
                value={currentPin}
                onChange={(e) => setCurrentPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
              />
            </div>
          )}
          <div>
            <Label htmlFor="new_pin">{status?.pin_configured ? "New PIN" : "Create a 4-digit PIN"}</Label>
            <Input
              id="new_pin"
              inputMode="numeric"
              maxLength={4}
              value={newPin}
              onChange={(e) => setNewPin(e.target.value.replace(/\D/g, "").slice(0, 4))}
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={save}
            loading={setPin.isPending}
            disabled={newPin.length !== 4 || (status?.pin_configured && currentPin.length !== 4)}
          >
            {status?.pin_configured ? "Change PIN" : "Create PIN"}
          </Button>
          {status?.pin_configured && (
            <button onClick={requestReset} className="text-xs text-[var(--brand)] hover:underline">
              Forgot your PIN?
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function SessionsCard() {
  const { toast } = useToast();
  const { data: sessions } = useSessions();
  const revoke = useRevokeSession();
  const revokeAll = useRevokeAllSessions();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2"><Monitor className="h-4 w-4" /> Active sessions</CardTitle>
        <CardDescription>Devices currently signed in to your account.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {sessions?.map((session) => (
          <div key={session.id} className="flex items-center justify-between rounded-xl bg-[var(--bg-inset)] p-3.5 text-sm">
            <div className="flex items-center gap-2.5">
              <Smartphone className="h-4 w-4 text-[var(--text-tertiary)]" />
              <div>
                <p className="text-[var(--text-primary)]">
                  {session.user_agent?.slice(0, 40) ?? "Unknown device"} {session.is_current && <Badge variant="brand">This device</Badge>}
                </p>
                <p className="text-xs text-[var(--text-tertiary)]">
                  Last used {session.last_used_at ? formatDateTime(session.last_used_at) : "just now"}
                </p>
              </div>
            </div>
            {!session.is_current && (
              <button
                onClick={async () => {
                  try {
                    await revoke.mutateAsync(session.id);
                    toast({ title: "Session signed out", variant: "success" });
                  } catch (error) {
                    toast({ title: "Could not sign out session", description: isApiError(error) ? error.message : undefined, variant: "error" });
                  }
                }}
                className="text-xs font-medium text-[var(--negative)] hover:underline"
              >
                Sign out
              </button>
            )}
          </div>
        ))}
        {(sessions?.length ?? 0) > 1 && (
          <Button
            variant="secondary"
            size="sm"
            onClick={async () => {
              try {
                await revokeAll.mutateAsync();
                toast({ title: "Signed out of all other devices", variant: "success" });
              } catch (error) {
                toast({ title: "Could not sign out sessions", description: isApiError(error) ? error.message : undefined, variant: "error" });
              }
            }}
          >
            <LogOut className="h-4 w-4" /> Sign out all other devices
          </Button>
        )}
      </CardContent>
    </Card>
  );
}
