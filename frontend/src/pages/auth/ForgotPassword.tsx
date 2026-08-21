import { useState } from "react";
import { Link } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { MailCheck } from "lucide-react";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError } from "@/components/ui/Input";
import { api, isApiError } from "@/lib/api";

const schema = z.object({ email: z.string().email("Enter a valid e-mail address.") });
type FormValues = z.infer<typeof schema>;

export function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await api.post("/auth/forgot-password", values);
      setSent(true);
    } catch (error) {
      setServerError(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  if (sent) {
    return (
      <AuthLayout title="Check your inbox">
        <div className="flex flex-col items-center gap-4 py-4 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[var(--brand-soft)]">
            <MailCheck className="h-7 w-7 text-[var(--brand)]" />
          </div>
          <p className="text-sm text-[var(--text-secondary)]">
            If an account exists for that e-mail, a reset link is on its way. The link expires in
            1 hour.
          </p>
          <Link to="/login" className="text-sm font-medium text-[var(--brand)] hover:underline">
            Back to sign in
          </Link>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Forgot your password?" subtitle="Enter your e-mail and we'll send you a reset link.">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <Label htmlFor="email">E-mail address</Label>
          <Input id="email" type="email" autoComplete="email" {...register("email")} error={!!errors.email} />
          <FieldError>{errors.email?.message}</FieldError>
        </div>
        {serverError && <p className="text-sm text-[var(--negative)]">{serverError}</p>}
        <Button type="submit" className="w-full" loading={isSubmitting}>
          Send reset link
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
