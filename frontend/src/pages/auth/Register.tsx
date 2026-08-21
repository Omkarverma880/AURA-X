import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { AuthLayout } from "@/components/auth/AuthLayout";
import { GoogleButton } from "@/components/auth/GoogleButton";
import { Button } from "@/components/ui/Button";
import { Input, Label, FieldError, FieldHint } from "@/components/ui/Input";
import { useAuth } from "@/contexts/AuthContext";
import { useAuthProviders } from "@/hooks/useAuthProviders";
import { isApiError } from "@/lib/api";

const schema = z
  .object({
    full_name: z.string().min(1, "Enter your name."),
    email: z.string().email("Enter a valid e-mail address."),
    password: z
      .string()
      .min(8, "At least 8 characters.")
      .refine((v) => !/^\d+$/.test(v) && !/^[a-zA-Z]+$/.test(v), {
        message: "Mix letters with numbers or symbols.",
      }),
    confirm: z.string(),
  })
  .refine((v) => v.password === v.confirm, { message: "Passwords do not match.", path: ["confirm"] });
type FormValues = z.infer<typeof schema>;

export function RegisterPage() {
  const { register: registerUser } = useAuth();
  const navigate = useNavigate();
  const { data: providers } = useAuthProviders();
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ resolver: zodResolver(schema) });

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await registerUser({ email: values.email, password: values.password, full_name: values.full_name });
      navigate("/dashboard", { replace: true });
    } catch (error) {
      setServerError(isApiError(error) ? error.message : "Something went wrong. Please try again.");
    }
  };

  return (
    <AuthLayout title="Create your account" subtitle="It takes less than a minute.">
      <div className="space-y-5">
        {providers?.google && <GoogleButton />}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="full_name">Full name</Label>
            <Input id="full_name" autoComplete="name" {...register("full_name")} error={!!errors.full_name} />
            <FieldError>{errors.full_name?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="email">E-mail address</Label>
            <Input id="email" type="email" autoComplete="email" {...register("email")} error={!!errors.email} />
            <FieldError>{errors.email?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              autoComplete="new-password"
              {...register("password")}
              error={!!errors.password}
            />
            <FieldHint>At least 8 characters, mixing letters with numbers or symbols.</FieldHint>
            <FieldError>{errors.password?.message}</FieldError>
          </div>
          <div>
            <Label htmlFor="confirm">Confirm password</Label>
            <Input
              id="confirm"
              type="password"
              autoComplete="new-password"
              {...register("confirm")}
              error={!!errors.confirm}
            />
            <FieldError>{errors.confirm?.message}</FieldError>
          </div>
          {serverError && <p className="text-sm text-[var(--negative)]">{serverError}</p>}
          <Button type="submit" className="w-full" loading={isSubmitting}>
            Create account
          </Button>
        </form>

        <p className="text-center text-sm text-[var(--text-secondary)]">
          Already have an account?{" "}
          <Link to="/login" className="font-medium text-[var(--brand)] hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
