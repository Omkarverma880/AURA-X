import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import * as THREE from "three";

import { softDotTexture } from "./softDot";
import { type AuraTier } from "./useAuraCapabilities";

export const GOLD = "#e8a83c";
export const GOLD_BRIGHT = "#ffd580";
export const GOLD_PALE = "#fff2d6";
/** The cool end of the gold range - an ember, never an actual blue. */
export const AURA_EMBER = "#ffb15c";

/**
 * The Aura X centrepiece: a glass ring lit from within.
 *
 * Two things make it read as one luminous object rather than a cloud of
 * sparks. First, a thin emissive torus gives the ring an unbroken structural
 * edge - without it the particles have nothing to describe and the eye reads
 * them as noise. Second, every particle is a soft radial sprite rather than
 * PointsMaterial's default hard square, so overlapping dust blends into light.
 *
 * Colour drifts between pale gold and a deeper ember around the
 * circumference, which gives the ring depth without ever leaving the warm
 * range.
 *
 * Motion follows one rule - luxury is slow.
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
  const dust = useRef<THREE.Group>(null);
  const { mouse } = useThree();

  useFrame((state) => {
    const t = state.clock.getElapsedTime();
    const progress = scrollProgress.current ?? 0;

    if (group.current) {
      group.current.rotation.z = t * 0.03;

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

      // Scroll response is intentionally quick to converge - at 0.06 the orb
      // visibly lagged the page, which reads as jank rather than weight.
      group.current.position.y = THREE.MathUtils.lerp(
        group.current.position.y,
        progress * 2.4,
        0.18,
      );
      group.current.position.z = THREE.MathUtils.lerp(
        group.current.position.z,
        progress * -3,
        0.18,
      );
      const breathe = 1 + Math.sin(t * 0.22) * 0.01;
      group.current.scale.setScalar(breathe * (1 - progress * 0.25));
    }

    // The dust drifts against the ring's own rotation, so the bright regions
    // migrate slowly rather than sitting on fixed particles.
    if (dust.current) dust.current.rotation.z = -t * 0.02;
  });

  const dense = tier === "high";

  return (
    <group ref={group} rotation={[0.5, 0, 0]}>
      {/* Exactly one circular edge in the whole composition.
          Do not add a second torus, a Fresnel-lit sphere, or anything else
          that draws its own outline at this radius - every attempt to layer
          a "glass thickness" or a glass ball here read on screen as two
          concentric rings. One ring, plus dust. */}
      <mesh>
        <torusGeometry args={[2.6, 0.008, 20, dense ? 260 : 128]} />
        <meshBasicMaterial color={GOLD_PALE} transparent opacity={0.9} />
      </mesh>
      {/* Two shells of soft dust. Far fewer particles than before - the
          structure now comes from the rim, so the dust only has to add
          atmosphere, and restraint is what keeps it from looking noisy. */}
      <group ref={dust}>
        <RingShell
          count={dense ? 1400 : 500}
          spread={0.045}
          size={0.075}
          opacity={0.55}
          warmth={0.85}
        />
        <RingShell
          count={dense ? 900 : 320}
          spread={0.17}
          size={0.14}
          opacity={0.22}
          warmth={0.45}
        />
      </group>
    </group>
  );
}

const RING_RADIUS = 2.6;

/**
 * One shell of ring dust: soft sprites scattered around the circumference
 * with a Gaussian falloff away from the ideal circle.
 *
 * `warmth` biases how much of the ring stays gold; the remainder drifts
 * toward the cool nebula tone. Per-point colour carries both that hue shift
 * and the brightness modulation, since PointsMaterial cannot vary size per
 * point without a custom shader.
 */
function RingShell({
  count,
  spread,
  size,
  opacity,
  warmth,
}: {
  count: number;
  spread: number;
  size: number;
  opacity: number;
  warmth: number;
}) {
  const texture = useMemo(() => softDotTexture(), []);

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const colors = new Float32Array(count * 3);
    const gold = new THREE.Color(GOLD_BRIGHT);
    const ember = new THREE.Color(AURA_EMBER);
    const mixed = new THREE.Color();

    // Box-Muller: clusters points near the ideal circle and thins outward,
    // giving a filament rather than an even band.
    const gaussian = () => {
      const u = Math.random() || 1e-6;
      const v = Math.random();
      return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
    };

    for (let i = 0; i < count; i += 1) {
      const angle = Math.random() * Math.PI * 2;
      const r = RING_RADIUS + gaussian() * spread;

      positions[i * 3] = Math.cos(angle) * r;
      positions[i * 3 + 1] = Math.sin(angle) * r;
      positions[i * 3 + 2] = gaussian() * spread;

      // One slow wave for temperature, another for brightness, on different
      // periods so neither repeats on an obvious interval.
      const cool = (Math.sin(angle * 1.0 - 1.1) + 1) / 2;
      mixed.copy(gold).lerp(ember, THREE.MathUtils.clamp(cool * (1 - warmth), 0, 0.75));

      const brightness =
        THREE.MathUtils.clamp(0.55 + 0.45 * Math.sin(angle * 2 + 0.6), 0.35, 1) *
        (0.7 + Math.random() * 0.5);

      colors[i * 3] = mixed.r * brightness;
      colors[i * 3 + 1] = mixed.g * brightness;
      colors[i * 3 + 2] = mixed.b * brightness;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    return geo;
  }, [count, spread, warmth]);

  return (
    <points geometry={geometry}>
      <pointsMaterial
        map={texture}
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
