import { Suspense, useEffect, useRef } from "react";
import { Canvas } from "@react-three/fiber";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";

import { AuraOrb, GOLD } from "./AuraOrb";
import { AuraPedestal } from "./AuraPedestal";
import { AuraParticles } from "./AuraParticles";
import { AuraFallback } from "./AuraFallback";
import { AURA_BUDGET, useAuraCapabilities, type AuraTier } from "./useAuraCapabilities";

/**
 * The Aura X hero scene.
 *
 * Chooses between the full WebGL composition and a CSS orb based on what the
 * device can actually sustain - see useAuraCapabilities. The scene is fixed
 * behind the page rather than scrolling with it, and responds to scroll by
 * receding, so the hero hands over to the sections below instead of being
 * abruptly torn down.
 */
export function AuraScene() {
  const { tier, ready, prefersReducedMotion } = useAuraCapabilities();

  // Written by a passive scroll listener and read inside useFrame - a ref, not
  // state, so scrolling never triggers a React render.
  const scrollProgress = useRef(0);

  useEffect(() => {
    const onScroll = () => {
      const heroHeight = window.innerHeight;
      scrollProgress.current = Math.min(1, window.scrollY / heroHeight);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Until detection has run, paint the fallback: it is cheap, needs no
  // context, and avoids a flash of empty black while we decide.
  if (!ready || tier === "none") {
    return (
      <div className="fixed inset-0 z-0">
        <AuraFallback animated={!prefersReducedMotion} />
      </div>
    );
  }

  return (
    <div className="fixed inset-0 z-0">
      <SceneCanvas tier={tier} scrollProgress={scrollProgress} />
    </div>
  );
}

function SceneCanvas({
  tier,
  scrollProgress,
}: {
  tier: Exclude<AuraTier, "none">;
  scrollProgress: React.RefObject<number>;
}) {
  const budget = AURA_BUDGET[tier];

  return (
    <Canvas
      camera={{ position: [0, 0.4, 7], fov: 45 }}
      dpr={budget.dpr}
      gl={{ antialias: tier === "high", powerPreference: "high-performance" }}
      // The hero is decorative; stop rendering entirely when the tab is
      // hidden or the canvas is scrolled off screen.
      frameloop="always"
      onCreated={(state) => {
        state.gl.toneMapping = THREE.ACESFilmicToneMapping;
        state.gl.toneMappingExposure = 1.15;
      }}
    >
      <color attach="background" args={["#050507"]} />
      <fog attach="fog" args={["#050507", 8, 17]} />

      <ambientLight intensity={0.06} />
      <pointLight position={[4, 3, 4]} intensity={0.18} color={GOLD} />
      <pointLight position={[6, 2, -2]} intensity={0.3} color="#5c7cfa" />

      <Suspense fallback={null}>
        <AuraParticles tier={tier} />
        <AuraOrb tier={tier} scrollProgress={scrollProgress} />
        <AuraPedestal reflector={budget.reflector} />

        {budget.bloom && (
          <EffectComposer>
            <Bloom
              intensity={tier === "high" ? 0.6 : 0.45}
              luminanceThreshold={0.32}
              luminanceSmoothing={0.25}
              mipmapBlur
            />
            <Vignette eskil={false} offset={0.2} darkness={1.1} />
          </EffectComposer>
        )}
      </Suspense>
    </Canvas>
  );
}
