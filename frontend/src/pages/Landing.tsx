import { useNavigate } from "react-router-dom";

import { AuraScene } from "@/components/aura/AuraScene";
import { useAuraReveal } from "@/components/aura/useAuraReveal";
import { HeroSection } from "@/components/landing/HeroSection";
import {
  WhatIsSection,
  DimensionsSection,
  PrivacySection,
  UniverseSection,
  FinalCta,
} from "@/components/landing/StorySections";

/**
 * The public landing page: a single cinematic descent into the Aura X
 * universe.
 *
 * The 3D scene is fixed behind the whole document rather than living inside
 * the hero, so scrolling moves the *content* past a stationary camera while
 * the orb itself recedes (AuraOrb reads scroll progress directly). That is
 * what keeps the page feeling like one continuous space instead of a hero
 * followed by a separate marketing page.
 */
export function LandingPage() {
  const navigate = useNavigate();
  const revealRef = useAuraReveal<HTMLDivElement>();

  const goToAuth = (mode: "login" | "register") =>
    navigate(mode === "login" ? "/login" : "/register");

  return (
    <div className="aura-surface relative min-h-dvh overflow-x-hidden">
      <AuraScene />

      {/* Content layer. The scene sits at z-0 and is pointer-events-none by
          virtue of being a bare canvas, so everything here stays clickable. */}
      <div ref={revealRef} className="relative z-10">
        <HeroSection onAuth={goToAuth} />
        <WhatIsSection />
        <DimensionsSection />
        <PrivacySection />
        <UniverseSection />
        <FinalCta onAuth={goToAuth} />
      </div>
    </div>
  );
}
