import { Link } from "react-router-dom";
import { Fingerprint, KeyRound, ShieldCheck, EyeOff } from "lucide-react";

import { DIMENSIONS } from "@/components/aura/dimensions";

/**
 * Everything below the hero.
 *
 * The 3D scene is fixed behind the entire page, so each section paints its own
 * backdrop - fading from transparent at the top of the scroll to near-solid
 * further down. The orb stays faintly visible through the upper sections,
 * which is what makes the page feel like one continuous descent into the
 * universe rather than a hero followed by an ordinary marketing page.
 */

function SectionLabel({ index, children }: { index: string; children: React.ReactNode }) {
  return (
    <p className="aura-reveal mb-5 flex items-center justify-center gap-3 text-[10px] uppercase tracking-[0.32em] text-white/35">
      <span className="text-[#e8a83c]/70">{index}</span>
      <span className="h-px w-8 bg-white/15" />
      {children}
    </p>
  );
}

export function WhatIsSection() {
  return (
    <section
      className="relative px-6 py-28 md:py-36"
      style={{
        background:
          "linear-gradient(180deg, transparent 0%, rgba(5,5,7,0.72) 26%, rgba(5,5,7,0.92) 100%)",
      }}
    >
      <div className="mx-auto max-w-2xl text-center">
        <SectionLabel index="02">What is Aura X</SectionLabel>
        <h2 className="aura-reveal text-balance text-3xl font-extralight leading-tight tracking-tight sm:text-5xl">
          A personal operating system for the things that{" "}
          <span className="text-[#e8a83c]">actually matter</span>.
        </h2>
        <p
          className="aura-reveal mx-auto mt-7 max-w-xl text-balance text-sm leading-relaxed text-white/55 sm:text-base"
          style={{ transitionDelay: "120ms" }}
        >
          Not another expense tracker. Aura X holds the ledger you keep with the
          people around you, the money you earn and spend, the wealth you are
          building, the goals you are chasing, the places you have been, and the
          moments you want to keep — in one quiet, private place.
        </p>
      </div>
    </section>
  );
}

export function DimensionsSection() {
  return (
    <section className="relative bg-[#050507] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-5xl">
        <SectionLabel index="03">Six dimensions</SectionLabel>

        <div className="mt-12 grid grid-cols-1 gap-px overflow-hidden rounded-2xl border border-white/[0.07] bg-white/[0.05] sm:grid-cols-2 lg:grid-cols-3">
          {DIMENSIONS.map((dimension, i) => (
            <article
              key={dimension.id}
              className="aura-reveal aura-glow group relative bg-[#08080d] p-7 transition-colors duration-500 hover:bg-[#0b0b12]"
              style={{ transitionDelay: `${i * 70}ms` }}
            >
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full border border-[#e8a83c]/25 text-[#e8a83c] transition-colors duration-500 group-hover:border-[#e8a83c]/60">
                  <dimension.icon className="h-4 w-4" strokeWidth={1.6} />
                </span>
                <span className="text-[10px] tracking-[0.28em] text-white/25">
                  {dimension.index}
                </span>
              </div>

              <h3 className="mt-5 text-lg font-light tracking-wide text-white">
                {dimension.label}
              </h3>
              <p className="mt-1.5 text-sm text-[#e8a83c]/80">{dimension.tagline}</p>
              <p className="mt-3 text-sm leading-relaxed text-white/45">
                {dimension.description}
              </p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

const PRIVACY_POINTS = [
  {
    icon: KeyRound,
    title: "Green PIN",
    body: "A second lock in front of your money. Salary, balances and spending stay masked until you enter it — and the server withholds the numbers entirely, so a locked session never receives them.",
  },
  {
    icon: Fingerprint,
    title: "Your data, only yours",
    body: "Every record is scoped to your account at the database layer. No shared tables, no cross-account reads, no exceptions.",
  },
  {
    icon: ShieldCheck,
    title: "Real authentication",
    body: "Argon2-hashed passwords, rotating refresh tokens, CSRF protection and rate limiting on every sensitive route.",
  },
  {
    icon: EyeOff,
    title: "Private by default",
    body: "Nothing is shared, published or sold. Aura X has no social feed and no advertiser — it is a private ledger that happens to be beautiful.",
  },
];

export function PrivacySection() {
  return (
    <section className="relative bg-[#050507] px-6 py-24 md:py-32">
      {/* A cold pool of light, to shift the temperature away from gold for the
          one section that is about protection rather than possession. */}
      <div
        className="pointer-events-none absolute left-1/2 top-0 h-96 w-[46rem] -translate-x-1/2 opacity-[0.16] blur-3xl"
        style={{ background: "radial-gradient(ellipse, #5c7cfa 0%, transparent 68%)" }}
      />

      <div className="relative mx-auto max-w-4xl">
        <SectionLabel index="04">Privacy &amp; control</SectionLabel>
        <h2 className="aura-reveal mx-auto max-w-2xl text-balance text-center text-3xl font-extralight leading-tight sm:text-4xl">
          Your numbers are yours to reveal.
        </h2>

        <div className="mt-14 grid grid-cols-1 gap-4 sm:grid-cols-2">
          {PRIVACY_POINTS.map((point, i) => (
            <div
              key={point.title}
              className="aura-reveal aura-panel p-6"
              style={{ transitionDelay: `${i * 80}ms` }}
            >
              <point.icon className="h-5 w-5 text-[#e8a83c]" strokeWidth={1.5} />
              <h3 className="mt-4 text-base font-light tracking-wide text-white">
                {point.title}
              </h3>
              <p className="mt-2 text-sm leading-relaxed text-white/45">{point.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

export function UniverseSection() {
  return (
    <section className="relative bg-[#050507] px-6 py-24 md:py-32">
      <div className="mx-auto max-w-3xl text-center">
        <SectionLabel index="05">One personal universe</SectionLabel>
        <h2 className="aura-reveal text-balance text-3xl font-extralight leading-tight sm:text-4xl">
          A trek you saved for is a{" "}
          <span className="text-[#e8a83c]">goal</span>, an{" "}
          <span className="text-[#e8a83c]">expense</span>, a{" "}
          <span className="text-[#e8a83c]">journey</span>, and a{" "}
          <span className="text-[#e8a83c]">memory</span>.
        </h2>
        <p
          className="aura-reveal mx-auto mt-7 max-w-xl text-balance text-sm leading-relaxed text-white/55 sm:text-base"
          style={{ transitionDelay: "120ms" }}
        >
          Most apps would make you file that in four different places, or pick
          one. Aura X keeps money, ambition and experience in the same universe,
          because that is how you actually live them.
        </p>
      </div>
    </section>
  );
}

export function FinalCta({ onAuth }: { onAuth: (mode: "login" | "register") => void }) {
  return (
    <section className="relative overflow-hidden bg-[#050507] px-6 pb-20 pt-24 md:pt-32">
      {/* The orb, returning as a horizon at the foot of the page. */}
      <div
        className="pointer-events-none absolute bottom-[-22rem] left-1/2 h-[34rem] w-[34rem] -translate-x-1/2 rounded-full opacity-55 blur-3xl"
        style={{ background: "radial-gradient(circle, rgba(232,168,60,0.55) 0%, transparent 62%)" }}
      />

      <div className="relative mx-auto max-w-xl text-center">
        <SectionLabel index="06">Begin</SectionLabel>
        <h2 className="aura-reveal text-balance text-4xl font-extralight tracking-tight sm:text-5xl">
          Enter your <span className="text-[#e8a83c]">Aura X</span>.
        </h2>

        <div className="aura-reveal mt-10 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <button
            onClick={() => onAuth("register")}
            className="group flex w-full items-center justify-center gap-2.5 rounded-full border border-[#e8a83c]/50 bg-[#e8a83c]/10 px-8 py-3.5 text-sm font-medium text-[#e8a83c] transition-all duration-500 hover:border-[#e8a83c] hover:bg-[#e8a83c]/20 sm:w-auto"
          >
            Create your universe
            <span aria-hidden className="transition-transform duration-500 group-hover:translate-x-1">
              →
            </span>
          </button>
          <button
            onClick={() => onAuth("login")}
            className="w-full rounded-full border border-white/12 px-8 py-3.5 text-sm text-white/70 transition-colors duration-500 hover:border-white/30 hover:text-white sm:w-auto"
          >
            I already have one
          </button>
        </div>

        <p className="mt-14 flex items-center justify-center gap-2 text-[11px] text-white/25">
          <ShieldCheck className="h-3.5 w-3.5 text-[#e8a83c]/50" />
          TLS-encrypted in transit · Green PIN protected finances
        </p>

        <p className="mt-4 text-[11px] text-white/20">
          Aura X · Your Money. Your Wealth. Your Goals. Your Life.{" "}
          <Link to="/login" className="underline-offset-4 hover:text-white/40 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </section>
  );
}
