import { cn } from "@/lib/utils";

/**
 * The Aura X mark, in miniature.
 *
 * This is the visual DNA that carries the landing page's identity into the
 * signed-in app - the same gold ring, orbiting dust and warm core, at a size
 * that can sit beside a greeting without asking for attention.
 *
 * Deliberately pure CSS rather than a second WebGL context: it appears on
 * pages the user works in all day, where a live canvas would cost battery for
 * no functional gain. Browsers also cap concurrent WebGL contexts, and
 * spending one on decoration risks the real scene losing its own.
 *
 * All motion is disabled under prefers-reduced-motion by the keyframes in
 * index.css, so this needs no guard of its own.
 */
export function AuraSigil({
  size = 44,
  className,
}: {
  size?: number;
  className?: string;
}) {
  return (
    <div
      className={cn("relative shrink-0", className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      {/* Ambient bloom. */}
      <div
        className="absolute inset-[-40%] rounded-full opacity-60 blur-lg"
        style={{ background: "radial-gradient(circle, rgba(232,168,60,0.5) 0%, transparent 65%)" }}
      />

      {/* The ring. */}
      <div
        className="absolute inset-0 rounded-full border border-[#e8a83c]/60"
        style={{ boxShadow: "0 0 12px rgba(232,168,60,0.45), inset 0 0 10px rgba(232,168,60,0.2)" }}
      />

      {/* Light travelling around it. */}
      <div
        className="aura-sigil-sweep absolute inset-0 rounded-full"
        style={{
          background:
            "conic-gradient(from 0deg, transparent 0deg, rgba(255,213,128,0.9) 50deg, transparent 120deg)",
          WebkitMask: "radial-gradient(circle, transparent 88%, #000 89%)",
          mask: "radial-gradient(circle, transparent 88%, #000 89%)",
        }}
      />

      {/* A single orbiting fragment. */}
      <div className="aura-sigil-orbit absolute inset-0">
        <span
          className="absolute left-1/2 top-0 h-1 w-1 -translate-x-1/2 rounded-full bg-[#ffd580]"
          style={{ boxShadow: "0 0 6px rgba(255,213,128,0.9)" }}
        />
      </div>

      {/* Warm core. */}
      <div
        className="aura-sigil-core absolute left-1/2 top-1/2 h-1.5 w-1.5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-[#ffd580]"
        style={{ boxShadow: "0 0 10px rgba(255,213,128,0.8)" }}
      />
    </div>
  );
}
