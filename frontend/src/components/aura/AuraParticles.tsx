import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Sparkles, Stars } from "@react-three/drei";
import * as THREE from "three";

import { GOLD } from "./AuraOrb";
import { AURA_BUDGET, type AuraTier } from "./useAuraCapabilities";

/**
 * Ambient depth: a starfield, a warm dust trail, and a cool cosmic haze far
 * behind the orb.
 *
 * IMPORTANT - drei `Sparkles` budget. This drei version mis-sizes the colour
 * buffer when `color` is given as a hex/THREE.Color (it multiplies the buffer
 * length by an extra factor of 3), and a *third* such instance reproducibly
 * blanks the whole canvas to black. Two are confirmed stable. AuraOrb already
 * uses one, this file uses the second, and the cool haze below is therefore a
 * hand-rolled THREE.Points cloud rather than a third Sparkles - which
 * sidesteps the bug entirely instead of relying on the two-instance limit
 * holding. Do not convert CosmicHaze back to <Sparkles>.
 */
export function AuraParticles({ tier }: { tier: Exclude<AuraTier, "none"> }) {
  const budget = AURA_BUDGET[tier];

  return (
    <>
      <Stars
        radius={70}
        depth={45}
        count={budget.stars}
        factor={2.6}
        saturation={0}
        fade
        speed={0.3}
      />

      {/* Warm dust drifting off to the left, like a comet tail the ring left
          behind. (Sparkles instance 2 of 2 - see the note above.) */}
      <Sparkles
        count={budget.trailDust}
        scale={[9, 5, 4]}
        position={[-5, -0.5, -2]}
        size={1.6}
        speed={0.09}
        color={GOLD}
        opacity={0.55}
        noise={1.2}
      />

      <CosmicHaze count={tier === "high" ? 260 : 90} />
    </>
  );
}

/**
 * A cold, very distant particle field, drifting almost imperceptibly.
 *
 * Hand-built rather than using drei's Sparkles - see the file header for why.
 * Positions are generated once and the whole cloud is rotated as a unit,
 * which costs one matrix update per frame instead of touching the buffer.
 */
function CosmicHaze({ count }: { count: number }) {
  const points = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    for (let i = 0; i < count; i += 1) {
      // Scattered through a shell well behind the orb, biased to one side so
      // it reads as a nebula rather than an even fog.
      const radius = 14 + Math.random() * 16;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(Math.random() * 2 - 1);
      positions[i * 3] = Math.sin(phi) * Math.cos(theta) * radius + 6;
      positions[i * 3 + 1] = Math.sin(phi) * Math.sin(theta) * radius * 0.5;
      positions[i * 3 + 2] = Math.cos(phi) * radius - 12;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geo;
  }, [count]);

  useFrame((state) => {
    if (!points.current) return;
    // One revolution takes roughly seventeen minutes.
    points.current.rotation.y = state.clock.getElapsedTime() * 0.006;
  });

  return (
    <points ref={points} geometry={geometry}>
      <pointsMaterial
        color="#5c7cfa"
        size={0.16}
        sizeAttenuation
        transparent
        opacity={0.4}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
