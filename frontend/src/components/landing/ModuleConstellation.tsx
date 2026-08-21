import { DIMENSIONS } from "@/components/aura/dimensions";

/**
 * The six dimensions arranged around the base of the orb, joined by faint
 * orbital lines.
 *
 * Not cards: each is an icon on a hairline ring, connected to its neighbours
 * by a thread of light, so they read as objects held in the orb's orbit
 * rather than a navigation row that happens to sit under the hero.
 */
export function ModuleConstellation() {
  return (
    <div className="relative mx-auto w-full max-w-5xl px-6">
      {/* The orbital thread the icons sit on. Hidden on small screens, where
          the six wrap onto a grid and a single line would connect nothing. */}
      <div
        className="pointer-events-none absolute left-6 right-6 top-5 hidden h-px md:block"
        style={{
          background:
            "linear-gradient(90deg, transparent 0%, rgba(232,168,60,0.28) 18%, rgba(232,168,60,0.42) 50%, rgba(232,168,60,0.28) 82%, transparent 100%)",
        }}
      />

      <ul className="grid grid-cols-3 gap-x-3 gap-y-7 md:grid-cols-6 md:gap-x-4">
        {DIMENSIONS.map((dimension, i) => (
          <li
            key={dimension.id}
            className="aura-reveal aura-drift flex flex-col items-center text-center"
            style={{
              // Each icon enters and drifts on its own offset, so the row
              // breathes instead of pulsing as one block.
              transitionDelay: `${i * 90}ms`,
              animationDelay: `${i * 1.3}s`,
            }}
          >
            <span
              className="relative flex h-10 w-10 items-center justify-center rounded-full border border-[#e8a83c]/30 bg-[#050507]"
              style={{ boxShadow: "0 0 18px rgba(232,168,60,0.18)" }}
            >
              <dimension.icon className="h-4 w-4 text-[#e8a83c]" strokeWidth={1.6} />
            </span>

            <p className="mt-2.5 text-[11px] font-medium tracking-wide text-white/90">
              {dimension.label}
            </p>
            <p className="mt-0.5 hidden text-[10px] leading-snug text-white/40 sm:block">
              {dimension.tagline}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
