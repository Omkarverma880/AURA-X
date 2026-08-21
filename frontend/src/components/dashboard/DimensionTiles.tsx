import { Link } from "react-router-dom";

import { DIMENSIONS } from "@/components/aura/dimensions";
import { cn } from "@/lib/utils";
import type { ModuleCard } from "@/types";

/**
 * The six dimensions as large, immersive tiles.
 *
 * Each carries its live headline from GET /dashboard where the API provides
 * one (`cards[].module` maps to `Dimension.moduleKey`). Journeys has no card
 * of its own - trips live inside the Memories module - so it falls back to its
 * static tagline rather than borrowing another module's numbers.
 *
 * Routing is unchanged: every tile is a plain <Link> to the route that module
 * already lived at.
 */
export function DimensionTiles({ cards }: { cards: ModuleCard[] }) {
  const byModule = new Map(cards.map((card) => [card.module, card]));

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {DIMENSIONS.map((dimension, i) => {
        const card = dimension.moduleKey ? byModule.get(dimension.moduleKey) : undefined;

        return (
          <Link
            key={dimension.id}
            to={dimension.route}
            className="aura-reveal aura-panel aura-panel-interactive aura-glow group relative block overflow-hidden p-5 sm:p-6"
            style={{ transitionDelay: `${i * 60}ms` }}
          >
            {/* Contextual artwork: a soft gold horizon that rises on hover.
                Abstract on purpose - stock photography would break the
                visual consistency the rest of the universe depends on. */}
            <div
              className="pointer-events-none absolute inset-x-0 bottom-0 h-24 opacity-40 transition-opacity duration-700 group-hover:opacity-80"
              style={{
                background:
                  "radial-gradient(ellipse 80% 100% at 50% 130%, rgba(232,168,60,0.28) 0%, transparent 70%)",
              }}
            />

            <div className="relative flex items-start justify-between gap-3">
              <span className="flex h-11 w-11 items-center justify-center rounded-2xl border border-[var(--aura-line)] bg-white/[0.02] text-[var(--aura-gold)] transition-colors duration-500 group-hover:border-[var(--aura-line-strong)]">
                <dimension.icon className="h-5 w-5" strokeWidth={1.5} />
              </span>
              <span className="text-[10px] tracking-[0.28em] text-[var(--aura-text-faint)]">
                {dimension.index}
              </span>
            </div>

            <div className="relative mt-5">
              <h3 className="text-base font-light tracking-wide text-[var(--aura-text)]">
                {dimension.label}
              </h3>
              <p className="mt-0.5 text-xs text-[var(--aura-gold)]/75">{dimension.tagline}</p>

              <p
                className={cn(
                  "mt-4 truncate text-lg font-light",
                  card?.locked
                    ? "tracking-[0.2em] text-[var(--aura-text-faint)]"
                    : "text-[var(--aura-text)]",
                )}
              >
                {card?.headline ?? dimension.description}
              </p>
              {card?.subtext && (
                <p className="mt-1 truncate text-xs text-[var(--aura-text-faint)]">
                  {card.subtext}
                </p>
              )}
            </div>
          </Link>
        );
      })}
    </div>
  );
}
