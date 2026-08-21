import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { type AuraTier } from "./useAuraCapabilities";

export const GOLD = "#e8a83c";
export const GOLD_BRIGHT = "#ffd580";
export const GOLD_PALE = "#fff2d6";

/**
 * The Aura X centrepiece: a ring built out of light rather than geometry.
 *
 * A solid torus reads as CGI - too even, too clean. What makes the reference
 * look photographic is that the ring is *made of particles*: a dense bright
 * filament at the core, a warmer scatter around it, and a wide dusty halo,
 * with brightness varying continuously around the circumference so parts of
 * the rim burn hotter than others. That is what this builds.
 *
 * Motion follows one rule - luxury is slow. Nothing completes a cycle in
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
  const hot = useRef<THREE.Group>(null);
  const { mouse } = useThree();

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const progress = scrollProgress.current ?? 0;

    if (group.current) {
      group.current.rotation.z = t * 0.035;

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

    // The hot arc drifts around the rim independently of the ring's own
    // rotation, so the bright region is never locked to the same particles.
    if (hot.current) hot.current.rotation.z = -t * 0.045;
  });

  const dense = tier === "high";

  return (
    <group ref={group} rotation={[0.5, 0, 0]}>
      {/* Smoked-glass interior: enough to seat the ring in a volume, sheer
          enough to keep the starfield visible through it. */}
      <mesh position={[0, 0, -0.05]}>
        <circleGeometry args={[2.56, 64]} />
        <meshBasicMaterial
          color="#05060a"
          transparent
          opacity={0.16}
          depthWrite={false}
          side={THREE.DoubleSide}
        />
      </mesh>

      {/* Three shells of dust, tightest and brightest first. Together they
          read as one luminous filament with atmosphere around it. */}
      <group ref={hot}>
        <RingShell
          count={dense ? 7000 : 1800}
          spread={0.014}
          size={0.011}
          color="#ffeccb"
          opacity={0.7}
        />
        <RingShell
          count={dense ? 6200 : 1600}
          spread={0.05}
          size={0.02}
          color={GOLD_BRIGHT}
          opacity={0.8}
        />
        <RingShell
          count={dense ? 4200 : 1000}
          spread={0.19}
          size={0.036}
          color={GOLD}
          opacity={0.34}
        />
      </group>
    </group>
  );
}

const RING_RADIUS = 2.6;

/**
 * One shell of the ring: points scattered around the circumference with a
 * Gaussian falloff away from the ideal circle.
 *
 * Per-point colour (not per-point size, which PointsMaterial cannot vary
 * without a custom shader) carries the brightness modulation, so some arcs
 * glow hot while others fade to embers. Stacking shells of different spreads
 * is what produces the soft-to-sharp gradient a single shell cannot.
 */
function RingShell({
  count,
  spread,
  size,
  color,
  opacity,
}: {
  count: number;
  spread: number;
  size: number;
  color: string;
  opacity: number;
}) {
  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const base = new THREE.Color(color);

    // Box-Muller: a normal distribution clusters points near the ideal circle
    // and thins outward, which is what gives a filament rather than a band.
    const gaussian = () => {
      const u = Math.random() || 1e-6;
      const v = Math.random();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    };

    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const radial = gaussian() * spread;
      const depth = gaussian() * spread;
      const r = RING_RADIUS + radial;

      positions[i * 3] = Math.cos(angle) * r;
      positions[i * 3 + 1] = Math.sin(angle) * r;
      positions[i * 3 + 2] = depth;

      // Two overlapping waves of different periods keep the bright regions
      // from repeating on an obvious interval.
      const wave =
        0.55 +
        0.45 * Math.sin(angle * 1 + 0.8) * 0.6 +
        0.35 * Math.sin(angle * 3 - 2.1) * 0.4;
      const intensity = THREE.MathUtils.clamp(wave, 0.42, 1) * (0.78 + Math.random() * 0.42);

      colors[i * 3] = base.r * intensity;
      colors[i * 3 + 1] = base.g * intensity;
      colors[i * 3 + 2] = base.b * intensity;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return geo;
  }, [count, spread, color]);

  return (
    <points geometry={geometry}>
      <pointsMaterial
        vertexColors
        size={size}
        sizeAttenuation
        transparent
        opacity={opacity}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}
