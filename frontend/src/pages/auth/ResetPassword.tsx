import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2 } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Label, FieldError, FieldHint } from "@/components/ui/Input";
import { PasswordInput } from "@/components/ui/PasswordInput";
import { api, isApiError } from "@/lib/api";

const schema = z
  .object({
    password: z.string().min(8, "At least 8 characters."),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { message: "Passwords do not match.", path: ["confirm"] });
type FormValues = z.infer<typeof schema>;

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [done, setDone] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const navigate = useNavigate();

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await api.post("/auth/reset-password", { token, new_password: values.password });
      setDone(true);
    } catch (error) {
      setServerError(isApiError(error) ? error.message : "This link is invalid or has expired.");
    }
  };

  if (!token) {
    return (
      <AuthLayout title="Invalid link">
        <p className="text-sm text-[var(--text-secondary)]">
          This password reset link is missing its token. Request a new one from the{" "}
          <Link to="/forgot-password" className="text-[var(--brand)] hover:underline">
            forgot password
          </Link>{" "}
          page.
        </p>
      </AuthLayout>
    );
  }

  if (done) {
    return (
      <AuthLayout title="Password updated">
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--positive-soft)]">
            <CheckCircle2 className="h-7 w-7 text-[var(--positive)]" />
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            You can now sign in with your new password.
          </p>
          <Button onClick={() => navigate("/login")}>Sign in</Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Set a new password">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="password">New password</Label>
          <PasswordInput id="password" autoComplete="new-password" {...register("password")} error={!!errors.password} />
          <FieldHint>At least 8 characters, mixing letters with numbers or symbols.</FieldHint>
          <FieldError>{errors.password?.message}</FieldError>
        </div>
        <div>
          <Label htmlFor="confirm">Confirm new password</Label>
          <PasswordInput id="confirm" autoComplete="new-password" {...register("confirm")} error={!!errors.confirm} />
          <FieldError>{errors.confirm?.message}</FieldError>
        </div>
        {serverError && <p className="text-sm text-[var(--negative)]">{serverError}</p>}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Update password
        </Button>
      </form>
    </AuthLayout>
  );
}
