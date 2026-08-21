/**
 * Kept as a re-export so any existing import of `HeroScene` keeps working.
 *
 * The scene itself now lives in components/aura/, split into the orb,
 * pedestal, particles and a CSS fallback, with a device-capability tier
 * deciding which of them actually render.
 */
export { AuraScene as HeroScene } from "@/components/aura/AuraScene";
