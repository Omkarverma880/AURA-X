import { useState } from "react";
import { Menu, X, ChevronDown } from "lucide-react";

import { ModuleConstellation } from "./ModuleConstellation";

/**
 * The first screen: navigation, the wordmark inside the orb, one call to
 * action, and the constellation of dimensions at the base.
 *
 * The 3D scene itself is fixed behind the whole page (see AuraScene), so this
 * component draws only the content that sits on top of it.
 */
export function HeroSection({ onAuth }: { onAuth: (mode: "login" | "register") => void }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <section className="relative flex min-h-dvh flex-col">
      <header className="flex items-center justify-between px-6 py-6 md:px-12 md:py-8">
        <span className="text-lg font-light tracking-[0.24em]">
          AURA <span className="font-semibold text-[#e8a83c]">X</span>
        </span>

        <div className="flex items-center gap-3">
          <button
            onClick={() => onAuth("register")}
            className="cursor-pointer rounded-full border border-white/15 bg-white/[0.03] px-5 py-2 text-sm font-medium text-[#e8a83c] backdrop-blur transition-colors duration-500 hover:border-[#e8a83c]/50 hover:bg-white/[0.07]"
          >
            Get Started
          </button>
          <button
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? "Close menu" : "Open menu"}
            aria-expanded={menuOpen}
            className="cursor-pointer rounded-full p-2 text-white/75 transition-colors duration-300 hover:bg-white/10 hover:text-white"
          >
            {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>

        {menuOpen && (
          <div className="absolute right-6 top-20 z-30 w-48 rounded-2xl border border-white/10 bg-black/85 p-2 backdrop-blur-md md:right-12">
            <button
              onClick={() => onAuth("login")}
              className="block w-full cursor-pointer rounded-xl px-3.5 py-2.5 text-left text-sm text-white/90 transition-colors hover:bg-white/10"
            >
              Sign in
            </button>
            <button
              onClick={() => onAuth("register")}
              className="block w-full cursor-pointer rounded-xl px-3.5 py-2.5 text-left text-sm text-white/90 transition-colors hover:bg-white/10"
            >
              Create account
            </button>
          </div>
        )}
      </header>

      {/* The wordmark sits inside the ring - the orb is centred slightly above
          the vertical middle of the viewport, and this matches it. */}
      <div className="flex flex-1 flex-col items-center justify-center px-6 pb-8 text-center">
        <h1 className="text-5xl font-extralight tracking-[0.14em] sm:text-7xl">
          AURA{" "}
          <span
            className="font-medium text-[#e8a83c]"
            style={{ textShadow: "0 0 28px rgba(232,168,60,0.65), 0 0 60px rgba(232,168,60,0.3)" }}
          >
            X
          </span>
        </h1>

        <p className="mt-6 max-w-sm text-balance text-sm leading-relaxed text-white/60 sm:text-base">
          Your Money. Your Wealth.
          <br />
          Your Goals. Your Life.
        </p>

        <button
          onClick={() => onAuth("register")}
          className="group mt-10 flex cursor-pointer items-center gap-2.5 rounded-full border border-[#e8a83c]/40 bg-black/30 px-7 py-3 text-sm font-medium text-[#e8a83c] backdrop-blur-sm transition-all duration-500 hover:border-[#e8a83c]/80 hover:bg-[#e8a83c]/10"
          style={{ boxShadow: "0 0 0 rgba(232,168,60,0)" }}
        >
          Explore Aura X
          <span
            aria-hidden
            className="transition-transform duration-500 group-hover:translate-x-1"
          >
            →
          </span>
        </button>
      </div>

      <div className="pb-10">
        <ModuleConstellation />

        <div className="mt-9 flex flex-col items-center gap-1.5 text-white/35">
          <ChevronDown className="h-4 w-4" />
          <span className="text-[10px] uppercase tracking-[0.28em]">Scroll to enter</span>
        </div>
      </div>
    </section>
  );
}
