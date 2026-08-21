import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { CheckCircle2, Eye, EyeOff } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, FieldHint } from "@/components/ui/Input";
import { api, isApiError } from "@/lib/api";

const schema = z
  .object({
    identifier: z.string().min(3, "Enter your e-mail, phone number or username."),
    new_password: z
      .string()
      .min(8, "Use at least 8 characters.")
      .refine(
        (v) => !/^\d+$/.test(v) && !/^[a-zA-Z]+$/.test(v),
        "Mix letters with numbers or symbols.",
      ),
    confirm_password: z.string(),
  })
  .refine((v) => v.new_password === v.confirm_password, {
    message: "Passwords do not match.",
    path: ["confirm_password"],
  });

type FormValues = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [done, setDone] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
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
      await api.post("/auth/recover-password", {
        identifier: values.identifier,
        new_password: values.new_password,
      });
      setDone(true);
    } catch (error) {
      setServerError(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  if (done) {
    return (
      <AuthLayout title="Password updated">
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--positive-soft)]">
            <CheckCircle2 className="h-7 w-7 text-[var(--positive-soft-text)]" />
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            If that account exists, its password has been updated. Any other devices
            that were signed in have been signed out.
          </p>
          <Button className="w-full" onClick={() => navigate("/login")}>
            Sign in
          </Button>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      title="Reset your password"
      subtitle="Tell us who you are and choose a new password."
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="identifier">E-mail, phone number or username</Label>
          <Input
            id="identifier"
            autoComplete="username"
            autoFocus
            {...register("identifier")}
            error={!!errors.identifier}
          />
          <FieldHint>Whichever you remember — any of the three works.</FieldHint>
          <FieldError>{errors.identifier?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="new_password">New password</Label>
          <div className="relative">
            <Input
              id="new_password"
              type={showPassword ? "text" : "password"}
              autoComplete="new-password"
              {...register("new_password")}
              error={!!errors.new_password}
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]"
              aria-label={showPassword ? "Hide password" : "Show password"}
            >
              {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
            </button>
          </div>
          <FieldError>{errors.new_password?.message}</FieldError>
        </div>

        <div>
          <Label htmlFor="confirm_password">Confirm new password</Label>
          <Input
            id="confirm_password"
            type={showPassword ? "text" : "password"}
            autoComplete="new-password"
            {...register("confirm_password")}
            error={!!errors.confirm_password}
          />
          <FieldError>{errors.confirm_password?.message}</FieldError>
        </div>

        {serverError && <p className="text-sm text-[var(--negative)]">{serverError}</p>}

        <Button type="submit" className="w-full" loading={isSubmitting}>
          Update password
        </Button>
        <Link
          to="/login"
          className="block text-center text-sm font-medium text-[var(--brand)] hover:underline"
        >
          Back to sign in
        </Link>
      </form>
    </AuthLayout>
  );
}
