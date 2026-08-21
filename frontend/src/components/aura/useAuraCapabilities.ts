import { useEffect, useState } from "react";

/**
 * What kind of Aura scene this device should be asked to render.
 *
 * "none" is not a failure state - it is a first-class design, rendered by
 * AuraFallback as a pure-CSS orb. A phone that would drop frames, a machine
 * with no WebGL, and a visitor who asked their OS for reduced motion all get
 * something that still looks like Aura X rather than an empty black rectangle.
 */
export type AuraTier = "high" | "low" | "none";

export interface AuraCapabilities {
  tier: AuraTier;
  /** True once detection has run; before that, render nothing heavy. */
  ready: boolean;
  prefersReducedMotion: boolean;
}

/** A cheap, cached WebGL probe - creating a context is not free, so do it once. */
let webglSupport: boolean | null = null;

function supportsWebGL(): boolean {
  if (webglSupport !== null) return webglSupport;
  try {
    const canvas = document.createElement("canvas");
    const gl =
      canvas.getContext("webgl2") ??
      canvas.getContext("webgl") ??
      canvas.getContext("experimental-webgl");
    webglSupport = Boolean(gl);
    // Release the probe context immediately; browsers cap how many exist at
    // once and the real Canvas needs one of those slots.
    if (gl && "getExtension" in gl) {
      (gl as WebGLRenderingContext).getExtension("WEBGL_lose_context")?.loseContext();
    }
  } catch {
    webglSupport = false;
  }
  return webglSupport;
}

/**
 * Decide between the full scene and the cheap one.
 *
 * Deliberately conservative: the cost of guessing "high" wrong is a janky
 * hero on someone's phone, while the cost of guessing "low" wrong is a
 * slightly simpler scene nobody notices.
 */
function detectTier(): AuraTier {
  if (typeof window === "undefined") return "none";
  if (!supportsWebGL()) return "none";

  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return "none";

  const cores = navigator.hardwareConcurrency ?? 4;
  const memory = (navigator as Navigator & { deviceMemory?: number }).deviceMemory ?? 4;
  const coarse = window.matchMedia("(pointer: coarse)").matches;
  const narrow = window.innerWidth < 768;

  if (cores <= 4 || memory <= 4) return "low";
  // Phones and tablets get the reduced scene even when they report plenty of
  // cores - sustained GPU load is what drains a battery and throttles, and a
  // hero animation is not worth either.
  if (coarse && narrow) return "low";

  return "high";
}

export function useAuraCapabilities(): AuraCapabilities {
  const [state, setState] = useState<AuraCapabilities>({
    tier: "none",
    ready: false,
    prefersReducedMotion: false,
  });

  useEffect(() => {
    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");

    const evaluate = () =>
      setState({
        tier: detectTier(),
        ready: true,
        prefersReducedMotion: motionQuery.matches,
      });

    evaluate();

    // Someone can flip reduced-motion mid-session, and rotating a tablet
    // changes the width test.
    motionQuery.addEventListener("change", evaluate);
    window.addEventListener("resize", evaluate);
    return () => {
      motionQuery.removeEventListener("change", evaluate);
      window.removeEventListener("resize", evaluate);
    };
  }, []);

  return state;
}

/** Per-tier scene budget, kept in one place so the knobs are comparable. */
export const AURA_BUDGET = {
  high: {
    stars: 2800,
    ringDust: 140,
    trailDust: 220,
    dpr: [1, 1.75] as [number, number],
    reflector: true,
    bloom: true,
  },
  low: {
    stars: 700,
    ringDust: 45,
    trailDust: 60,
    dpr: [1, 1.25] as [number, number],
    reflector: false,
    bloom: true,
  },
} as const;
