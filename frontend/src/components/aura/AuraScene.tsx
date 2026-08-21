import { Suspense, useEffect, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
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

  const [inView, setInView] = useState(true);

  useEffect(() => {
    const onScroll = () => {
      const heroHeight = window.innerHeight;
      scrollProgress.current = Math.min(1, window.scrollY / heroHeight);
      // Past ~1.4 viewports the scene is completely hidden behind the opaque
      // sections below, so there is nothing to gain from still drawing it.
      setInView(window.scrollY < heroHeight * 1.4);
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
      <SceneCanvas tier={tier} scrollProgress={scrollProgress} active={inView} />
    </div>
  );
}

/**
 * Keeps the whole orb in frame on any viewport.
 *
 * A perspective camera's `fov` is *vertical*, so the horizontal field of view
 * shrinks with the aspect ratio. On a 390px-wide phone that put the ring's
 * left and right edges off screen at the distance that frames it perfectly on
 * a laptop. Backing the camera off as the viewport narrows keeps the ring's
 * full diameter visible instead of scaling the desktop composition down.
 */
function ResponsiveCamera() {
  const { camera, size } = useThree();

  useEffect(() => {
    const aspect = size.width / size.height;
    // The ring spans ~4.8 units across after the scene's 0.92 scale; leave a
    // margin so the rim never touches the edge.
    const needed = 2.9 / Math.tan((45 * Math.PI) / 360);
    const distance = aspect >= 1 ? 8.9 : 8.9 + (1 / aspect - 1) * needed * 1.35;

    camera.position.set(0, aspect >= 1 ? 0.25 : 0.1, distance);
    camera.updateProjectionMatrix();
  }, [camera, size.width, size.height]);

  return null;
}

function SceneCanvas({
  tier,
  scrollProgress,
  active,
}: {
  tier: Exclude<AuraTier, "none">;
  scrollProgress: React.RefObject<number>;
  active: boolean;
}) {
  const budget = AURA_BUDGET[tier];

  return (
    <Canvas
      camera={{ position: [0, 0.25, 8.9], fov: 45 }}
      dpr={budget.dpr}
      gl={{ antialias: tier === "high", powerPreference: "high-performance" }}
      // The hero is decorative: once it is scrolled out of sight the loop
      // stops completely rather than burning a frame budget nobody can see.
      frameloop={active ? "always" : "never"}
      onCreated={(state) => {
        state.gl.toneMapping = THREE.ACESFilmicToneMapping;
        state.gl.toneMappingExposure = 1.15;
      }}
    >
      <ResponsiveCamera />
      <color attach="background" args={["#050507"]} />
      <fog attach="fog" args={["#050507", 10, 21]} />

      <ambientLight intensity={0.06} />
      <pointLight position={[4, 3, 4]} intensity={0.18} color={GOLD} />
      <pointLight position={[6, 2, -2]} intensity={0.3} color="#5c7cfa" />

      <Suspense fallback={null}>
        <AuraParticles tier={tier} />

        {/* Ball and dais move as one unit: lifted so the dais clears the
            module shelf, and scaled down because the dais now sits a full
            sphere-radius below the ring rather than inside it. */}
        <group position={[0, 1.0, 0]} scale={0.74}>
          <AuraOrb tier={tier} scrollProgress={scrollProgress} />
          <AuraPedestal />
        </group>

        {budget.bloom && (
          <EffectComposer>
            <Bloom
              intensity={tier === "high" ? 1.05 : 0.75}
              luminanceThreshold={0.45}
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
