import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Sparkles } from "@react-three/drei";
import * as THREE from "three";

import { AURA_BUDGET, type AuraTier } from "./useAuraCapabilities";

export const GOLD = "#e8a83c";
export const GOLD_BRIGHT = "#ffd580";
export const GOLD_PALE = "#fff2d6";

/**
 * The Aura X centrepiece: a gold ring seen in perspective, with light
 * travelling around it and fragments drifting free of its rim.
 *
 * Motion follows one rule - luxury is slow. Nothing here completes a cycle in
 * under twenty seconds, so the object reads as alive rather than animated.
 */
export function AuraOrb({
  tier,
  scrollProgress,
}: {
  tier: Exclude<AuraTier, "none">;
  /** 0 at the top of the hero, 1 once it has scrolled away. */
  scrollProgress: React.RefObject<number>;
}) {
  const group = useRef<THREE.Group>(null);
  const arcA = useRef<THREE.Mesh>(null);
  const arcB = useRef<THREE.Mesh>(null);
  const shards = useRef<THREE.Group>(null);
  const { mouse } = useThree();
  const budget = AURA_BUDGET[tier];

  // Fragments that have broken away from the ring. Positions are seeded once;
  // the frame loop only eases them in and out along their own axis.
  const fragments = useMemo(
    () =>
      Array.from({ length: tier === "high" ? 9 : 5 }, (_, i) => {
        const angle = (i / (tier === "high" ? 9 : 5)) * Math.PI * 2;
        return {
          angle,
          // Each fragment breathes on its own period so they never pulse in
          // unison, which would read as a mechanical blink.
          period: 9 + (i % 4) * 3.5,
          phase: i * 1.7,
          size: 0.02 + (i % 3) * 0.008,
          arc: 0.06 + (i % 2) * 0.04,
        };
      }),
    [tier],
  );

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const progress = scrollProgress.current ?? 0;

    if (group.current) {
      group.current.rotation.z = t * 0.05;

      // Parallax toward the cursor, heavily damped so it feels like weight
      // rather than a cursor-follower.
      group.current.rotation.x = THREE.MathUtils.lerp(
        group.current.rotation.x,
        0.5 + mouse.y * 0.05,
        0.025,
      );
      group.current.rotation.y = THREE.MathUtils.lerp(
        group.current.rotation.y,
        mouse.x * 0.08,
        0.025,
      );

      // As the hero scrolls away the orb rises and recedes, handing the
      // screen to the sections below instead of being abruptly unmounted.
      group.current.position.y = THREE.MathUtils.lerp(
        group.current.position.y,
        progress * 2.4,
        0.06,
      );
      group.current.position.z = THREE.MathUtils.lerp(
        group.current.position.z,
        progress * -3,
        0.06,
      );
      const breathe = 1 + Math.sin(t * 0.22) * 0.012;
      group.current.scale.setScalar(breathe * (1 - progress * 0.25));
    }

    // Light travelling around the rim: two arcs at different speeds, so the
    // brighter one periodically laps the softer one.
    if (arcA.current) arcA.current.rotation.z = -t * 0.16;
    if (arcB.current) arcB.current.rotation.z = -t * 0.1 + 1.2;

    if (shards.current) {
      shards.current.children.forEach((shard, i) => {
        const f = fragments[i];
        if (!f) return;
        // A slow triangle wave: drift out, hold, ease back to the rim.
        const cycle = ((t + f.phase) % f.period) / f.period;
        const out = Math.sin(cycle * Math.PI) ** 2;
        const radius = 2.6 + out * 0.34;
        shard.position.set(
          Math.cos(f.angle) * radius,
          Math.sin(f.angle) * radius,
          out * 0.16,
        );
        const material = (shard as THREE.Mesh).material as THREE.MeshBasicMaterial;
        material.opacity = 0.25 + (1 - out) * 0.6;
      });
    }
  });

  return (
    <group ref={group} rotation={[0.5, 0, 0]}>
      {/* The ring itself. */}
      <mesh>
        <torusGeometry args={[2.6, 0.018, 24, tier === "high" ? 220 : 110]} />
        <meshStandardMaterial
          color={GOLD}
          emissive={GOLD_BRIGHT}
          emissiveIntensity={0.85}
          roughness={0.25}
          metalness={0.7}
        />
      </mesh>

      {/* Inner disc: barely-there smoked glass so the ring encloses a volume
          rather than framing empty space. */}
      <mesh position={[0, 0, -0.04]}>
        <circleGeometry args={[2.58, 64]} />
        <meshBasicMaterial
          color="#05060a"
          transparent
          opacity={0.16}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Energy travelling the rim. */}
      <mesh ref={arcA}>
        <torusGeometry args={[2.63, 0.009, 16, 180, Math.PI * 1.1]} />
        <meshBasicMaterial color={GOLD_BRIGHT} transparent opacity={0.45} />
      </mesh>
      <mesh ref={arcB}>
        <torusGeometry args={[2.67, 0.004, 16, 180, Math.PI * 0.7]} />
        <meshBasicMaterial color={GOLD_PALE} transparent opacity={0.3} />
      </mesh>

      {/* Fragments breaking away and reforming. */}
      <group ref={shards}>
        {fragments.map((f, i) => (
          <mesh key={i}>
            <boxGeometry args={[f.size * 3.5, f.size, f.size]} />
            <meshBasicMaterial color={GOLD_BRIGHT} transparent opacity={0.7} />
          </mesh>
        ))}
      </group>

      {/* Fine gold dust hugging the rim. */}
      <Sparkles
        count={budget.ringDust}
        scale={[6, 6, 0.3]}
        size={2.2}
        speed={0.12}
        color={GOLD_BRIGHT}
        opacity={0.8}
        noise={0.4}
      />
    </group>
  );
}
