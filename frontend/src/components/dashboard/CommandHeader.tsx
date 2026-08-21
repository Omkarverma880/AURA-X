import { Lock, Unlock } from "lucide-react";

import { AuraSigil } from "@/components/aura/AuraSigil";
import { useFinancial } from "@/contexts/FinancialContext";
import { formatDate } from "@/lib/format";
import type { GreetingBlock } from "@/types";

/**
 * The masthead of the command centre: who you are, when it is, and whether
 * your money is currently visible.
 *
 * The privacy indicator is read-only status plus a way in - it reflects the
 * FinancialContext, which mirrors the server. It never decides anything: the
 * server withholds locked figures regardless of what this shows.
 */
export function CommandHeader({
  greeting,
  fallbackName,
}: {
  greeting: GreetingBlock;
  fallbackName?: string;
}) {
  const { isUnlocked, isPinConfigured, secondsRemaining, promptUnlock, lock } = useFinancial();

  return (
    <header className="relative overflow-hidden px-5 pb-8 pt-8 md:px-10 md:pb-10 md:pt-12">
      {/* The orb's light, arriving from off-screen - the same warmth that lit
          the landing page, now behind the greeting. */}
      <div
        className="pointer-events-none absolute -top-40 left-1/2 h-96 w-[52rem] -translate-x-1/2 opacity-[0.22] blur-3xl"
        style={{ background: "radial-gradient(ellipse, rgba(232,168,60,0.7) 0%, transparent 68%)" }}
      />

      <div className="relative flex flex-wrap items-center justify-between gap-5">
        <div className="flex items-center gap-4">
          <AuraSigil size={46} />
          <div>
            <h1 className="text-2xl font-extralight tracking-tight text-[var(--aura-text)] sm:text-3xl">
              {greeting.greeting},{" "}
              <span className="font-normal">
                {greeting.name || fallbackName?.split(" ")[0]}
              </span>
            </h1>
            <p className="mt-1 text-xs tracking-wide text-[var(--aura-text-faint)]">
              Your universe at a glance · {formatDate(greeting.date, "long")}
            </p>
          </div>
        </div>

        {isPinConfigured && (
          <button
            type="button"
            onClick={() => (isUnlocked ? void lock() : promptUnlock())}
            className="group flex items-center gap-2.5 rounded-full border px-4 py-2 text-xs transition-colors duration-500"
            style={{
              borderColor: isUnlocked ? "rgba(74,222,128,0.32)" : "var(--aura-line-strong)",
              color: isUnlocked ? "#86efac" : "var(--aura-gold)",
              background: isUnlocked ? "rgba(74,222,128,0.06)" : "rgba(232,168,60,0.06)",
            }}
          >
            {isUnlocked ? <Unlock className="h-3.5 w-3.5" /> : <Lock className="h-3.5 w-3.5" />}
            <span className="tracking-[0.14em] uppercase">
              {isUnlocked ? "Private mode open" : "Private mode active"}
            </span>
            {isUnlocked && secondsRemaining > 0 && (
              <span className="tabular-nums text-[var(--aura-text-faint)]">
                {Math.floor(secondsRemaining / 60)}:
                {String(secondsRemaining % 60).padStart(2, "0")}
              </span>
            )}
          </button>
        )}
      </div>
    </header>
  );
}
