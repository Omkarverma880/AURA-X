import type { CSSProperties, ReactNode } from "react";
import { HandCoins, TrendingUp, Target } from "lucide-react";

/**
 * Gold/black palette for every pre-auth screen (login, register, forgot/reset
 * password, verify e-mail), overriding the design system's CSS custom
 * properties for this subtree only. Every shared component - Button, Input,
 * Select, links styled with `text-[var(--brand)]` - reads its colour from
 * these same variables, so scoping the override here re-themes all of them
 * automatically without touching a single component file. The interior app
 * (dashboard onward) is untouched: it still resolves the default palette
 * from :root once the user is past this layout.
 */
const AURA_VARS = {
  "--brand": "#e8a83c",
  "--brand-hover": "#f2c368",
  "--brand-soft": "rgba(232, 168, 60, 0.14)",
  "--brand-soft-text": "#f2c368",
  "--on-brand": "#0b0b0f",

  "--bg-base": "#050507",
  "--bg-surface": "#0d0d11",
  "--bg-surface-hover": "#17171d",
  "--bg-inset": "#121216",
  "--bg-overlay": "rgba(0, 0, 0, 0.7)",

  "--border-subtle": "#1c1c22",
  "--border-default": "#28282f",

  "--text-primary": "#f5f5f7",
  "--text-secondary": "#a3a3ae",
  "--text-tertiary": "#6f6f7a",
  "--text-inverse": "#0b0b0f",

  "--positive": "#4ade80",
  "--positive-soft": "rgba(74, 222, 128, 0.12)",
  "--positive-soft-text": "#86efac",
  "--negative": "#f87171",
  "--negative-soft": "rgba(248, 113, 113, 0.12)",
  "--negative-soft-text": "#fca5a5",
} as CSSProperties;

export function AuthLayout({ title, subtitle, children }: { title: string; subtitle?: string; children: ReactNode }) {
  return (
    <div style={AURA_VARS} className="grid min-h-dvh bg-[var(--bg-base)] text-[var(--text-primary)] md:grid-cols-2">
      {/* Branding panel - hidden on small screens to keep the form front and centre */}
      <div className="relative hidden flex-col justify-between overflow-hidden border-r border-[var(--border-subtle)] p-10 md:flex">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-[var(--brand)]/20 blur-[100px]" />
        <div className="absolute -bottom-32 -left-16 h-96 w-96 rounded-full bg-[var(--brand)]/10 blur-[100px]" />
        <div className="pointer-events-none absolute inset-0 opacity-[0.15] [background-image:radial-gradient(circle,white_1px,transparent_1px)] [background-size:28px_28px]" />

        <div className="relative flex items-center gap-2.5">
          <span className="text-lg font-semibold tracking-[0.2em]">
            AURA <span className="text-[var(--brand)]">X</span>
          </span>
        </div>

        <div className="relative space-y-6">
          <h1 className="text-4xl font-light leading-tight tracking-wide">
            Your Money.
            <br />
            Your Wealth.
            <br />
            <span className="font-semibold text-[var(--brand)]">Your Goals. Your Life.</span>
          </h1>
          <p className="max-w-sm text-[var(--text-secondary)]">
            One place to track what you lend, what you spend, what you invest and what you want
            out of life.
          </p>
          <div className="flex gap-6 pt-2 text-sm text-[var(--text-secondary)]">
            <span className="flex items-center gap-1.5"><HandCoins className="h-4 w-4 text-[var(--brand)]" /> Bahi Khata</span>
            <span className="flex items-center gap-1.5"><TrendingUp className="h-4 w-4 text-[var(--brand)]" /> Investments</span>
            <span className="flex items-center gap-1.5"><Target className="h-4 w-4 text-[var(--brand)]" /> Goals</span>
          </div>
        </div>

        <p className="relative text-xs text-[var(--text-tertiary)]">
          Bank-grade security · Argon2id password hashing · Green PIN protected finances
        </p>
      </div>

      <div className="flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-sm">
          <div className="mb-8 flex items-center gap-2.5 md:hidden">
            <span className="text-base font-semibold tracking-[0.2em]">
              AURA <span className="text-[var(--brand)]">X</span>
            </span>
          </div>

          <h2 className="text-2xl font-bold text-[var(--text-primary)]">{title}</h2>
          {subtitle && <p className="mt-1.5 text-sm text-[var(--text-secondary)]">{subtitle}</p>}

          <div className="mt-7">{children}</div>
        </div>
      </div>
    </div>
  );
}
