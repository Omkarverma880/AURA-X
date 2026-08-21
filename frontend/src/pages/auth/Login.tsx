import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Mail, Smartphone } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { PhoneLoginPanel } from "@/components/auth/PhoneLoginPanel";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError } from "@/components/ui/Input";
import { useAuth } from "@/contexts/AuthContext";
import { useAuthProviders } from "@/hooks/useAuthProviders";
import { isApiError } from "@/lib/api";

const schema = z.object({
  email: z.string().email("Enter a valid e-mail address."),
  password: z.string().min(1, "Enter your password."),
});
type FormValues = z.infer<typeof schema>;

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { data: providers } = useAuthProviders();
  const [mode, setMode] = useState<"email" | "phone">("email");
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await login(values);
      const from = (location.state as { from?: Location })?.from?.pathname ?? "/dashboard";
      navigate(from, { replace: true });
    } catch (error) {
      setServerError(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  return (
    <AuthLayout title="Welcome back" subtitle="Sign in to continue to your Aura X.">
      <div className="space-y-5">
        {providers?.google && <GoogleButton />}

        <div className="flex rounded-xl bg-[var(--bg-inset)] p-1 text-sm">
          <button
            type="button"
            onClick={() => setMode("email")}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 font-medium transition-colors ${mode === "email" ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-soft" : "text-[var(--text-tertiary)]"}`}
          >
            <Mail className="h-3.5 w-3.5" /> E-mail
          </button>
          <button
            type="button"
            onClick={() => setMode("phone")}
            className={`flex flex-1 items-center justify-center gap-1.5 rounded-lg py-2 font-medium transition-colors ${mode === "phone" ? "bg-[var(--bg-surface)] text-[var(--text-primary)] shadow-soft" : "text-[var(--text-tertiary)]"}`}
          >
            <Smartphone className="h-3.5 w-3.5" /> Phone
          </button>
        </div>

        {mode === "phone" ? (
          <PhoneLoginPanel />
        ) : (
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div>
              <Label htmlFor="email">E-mail address</Label>
              <Input id="email" type="email" autoComplete="email" {...register("email")} error={!!errors.email} />
              <FieldError>{errors.email?.message}</FieldError>
            </div>
            <div>
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot-password" className="text-xs text-[var(--brand)] hover:underline">
                  Forgot password?
                </Link>
              </div>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                {...register("password")}
                error={!!errors.password}
              />
              <FieldError>{errors.password?.message}</FieldError>
            </div>
            {serverError && <p className="text-sm text-[var(--negative)]">{serverError}</p>}
            <Button type="submit" className="w-full" loading={isSubmitting}>
              Sign in
            </Button>
          </form>
        )}

        <p className="text-center text-sm text-[var(--text-secondary)]">
          New to Aura X?{" "}
          <Link to="/register" className="font-medium text-[var(--brand)] hover:underline">
            Create an account
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
