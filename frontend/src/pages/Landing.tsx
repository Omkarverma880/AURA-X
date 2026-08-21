import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Menu, X, ChevronDown, Wallet, PiggyBank, TrendingUp, Target, Mountain, Images, ShieldCheck } from "lucide-react";
import { HeroScene } from "@/components/landing/HeroScene";

const MODULES = [
  { icon: Wallet, label: "Bahi Khata", sub: "Give, take & balances" },
  { icon: PiggyBank, label: "Spend", sub: "Track income & expenses" },
  { icon: TrendingUp, label: "Wealth", sub: "Investments & growth" },
  { icon: Target, label: "Goals", sub: "Plan. Achieve. Repeat." },
  { icon: Mountain, label: "Journeys", sub: "Places. Treks. Experiences." },
  { icon: Images, label: "Memories", sub: "Capture. Cherish. Relive." },
];

export function LandingPage() {
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const goToAuth = (mode: "login" | "register") => navigate(mode === "login" ? "/login" : "/register");

  return (
    <div className="relative min-h-dvh overflow-x-hidden bg-[#050507] text-white">
      <HeroScene />

      {/* Content sits above the canvas; the canvas itself never intercepts
          clicks meant for the page (Canvas defaults to pointer passthrough
          only for its own contents, so nav/buttons above it work normally). */}
      <div className="relative z-10 flex min-h-dvh flex-col">
        <header className="flex items-center justify-between px-6 py-6 md:px-12 md:py-8">
          <span className="text-lg font-semibold tracking-[0.2em]">
            AURA <span className="text-[#e8a83c]">X</span>
          </span>

          <div className="flex items-center gap-3">
            <button
              onClick={() => goToAuth("register")}
              className="rounded-full border border-white/15 bg-white/[0.03] px-5 py-2 text-sm font-medium text-[#e8a83c] backdrop-blur transition-colors hover:bg-white/10"
            >
              Get Started
            </button>
            <button
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Menu"
              className="rounded-full p-2 text-white/80 transition-colors hover:bg-white/10 hover:text-white"
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>

          {menuOpen && (
            <div className="absolute right-6 top-20 z-20 w-48 rounded-2xl border border-white/10 bg-black/80 p-2 backdrop-blur-md md:right-12">
              <button
                onClick={() => goToAuth("login")}
                className="block w-full rounded-xl px-3.5 py-2.5 text-left text-sm text-white/90 hover:bg-white/10"
              >
                Sign in
              </button>
              <button
                onClick={() => goToAuth("register")}
                className="block w-full rounded-xl px-3.5 py-2.5 text-left text-sm text-white/90 hover:bg-white/10"
              >
                Create account
              </button>
            </div>
          )}
        </header>

        <main className="flex flex-1 flex-col items-center justify-center px-6 text-center">
          <h1 className="text-5xl font-light tracking-[0.12em] sm:text-7xl">
            AURA <span className="font-semibold text-[#e8a83c]">X</span>
          </h1>
          <p className="mt-5 max-w-md text-balance text-base text-white/70 sm:text-lg">
            Your Money. Your Wealth.
            <br />
            Your Goals. Your Life.
          </p>
          <button
            onClick={() => goToAuth("register")}
            className="mt-9 flex items-center gap-2 rounded-full border border-[#e8a83c]/50 bg-[#e8a83c]/10 px-7 py-3 text-sm font-medium text-[#e8a83c] backdrop-blur transition-all hover:border-[#e8a83c] hover:bg-[#e8a83c]/20"
          >
            Explore Aura X
            <span aria-hidden>→</span>
          </button>
        </main>

        <footer className="px-6 pb-10 md:px-12">
          <div className="mx-auto grid max-w-5xl grid-cols-2 gap-x-4 gap-y-6 sm:grid-cols-3 md:grid-cols-6">
            {MODULES.map((module) => (
              <div key={module.label} className="flex items-center gap-2.5 sm:flex-col sm:items-center sm:text-center sm:gap-2">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#e8a83c]/30 text-[#e8a83c]">
                  <module.icon className="h-4 w-4" strokeWidth={1.75} />
                </div>
                <div className="sm:mt-0">
                  <p className="text-xs font-medium text-white">{module.label}</p>
                  <p className="hidden text-[10px] text-white/50 sm:block">{module.sub}</p>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-8 flex items-center justify-center gap-1.5 text-[11px] text-white/40">
            <ShieldCheck className="h-3.5 w-3.5 text-[#e8a83c]/70" />
            <span>Bank-grade security · TLS-encrypted in transit · Green PIN protected finances</span>
          </div>

          <div className="mt-6 flex flex-col items-center gap-1.5 text-white/40">
            <ChevronDown className="h-4 w-4 animate-bounce" />
            <span className="text-[11px] uppercase tracking-[0.2em]">Scroll to explore</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
