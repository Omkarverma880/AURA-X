import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

import { GOLD, GOLD_BRIGHT } from "./AuraOrb";
import { softDotTexture } from "./softDot";

/**
 * The dais the glass ball rests on.
 *
 * Geometry note - the tilt matters. The ring has radius 2.6, but AuraOrb
 * tilts it 0.5 rad about X, so a point at ring angle t sits at
 * y = 2.6 * sin(t) * cos(0.5). Its lowest point is therefore
 * -2.6 * cos(0.5) = -2.282, NOT -2.6. Positioning the top tier for an
 * untilted ring left the ring visibly floating ~0.39 units above the dais.
 * RING_LOW below is derived rather than hard-coded so the two cannot drift
 * apart again if the tilt is ever changed.
 *
 * The tiers are unlit on purpose: a lit metal under the warm key light plus
 * ACES tone mapping plus bloom kept returning a brass wash no matter how it
 * was tuned. Unlit means they are exactly this dark navy, always, and every
 * bit of warmth comes from the rim rings.
 */
/** Ring tilt, in radians - must match the rotation applied in AuraOrb. */
const RING_TILT = 0.5;
/** World-space y of the lowest point of the tilted ring. */
const RING_LOW = -2.6 * Math.cos(RING_TILT);

export function AuraPedestal() {
  const core = useRef<THREE.Mesh>(null);

  const tiers = useMemo(
    () => [
      // y is the centre, offset down from RING_LOW so the top tier's surface
      // meets the bottom of the ring exactly. Tops are spaced closer than the
      // heights, so consecutive tiers overlap and leave no gap between steps.
      { radius: 1.9, height: 0.24, y: RING_LOW - 0.12 },
      { radius: 2.4, height: 0.24, y: RING_LOW - 0.3 },
      { radius: 2.9, height: 0.22, y: RING_LOW - 0.47 },
      { radius: 3.4, height: 0.2, y: RING_LOW - 0.63 },
    ],
    [],
  );

  useFrame((state) => {
    if (!core.current) return;
    // A slow tide in the light at the base - the only thing on screen that
    // pulses, and it takes eleven seconds to do it once.
    const t = state.clock.getElapsedTime();
    const material = core.current.material as THREE.MeshBasicMaterial;
    material.opacity = 0.5 + Math.sin(t * 0.57) * 0.18;
  });

  return (
    <group>
      {tiers.map((tier, i) => (
        <group key={i} position={[0, tier.y, 0]}>
          <mesh>
            <cylinderGeometry args={[tier.radius, tier.radius, tier.height, 72]} />
            <meshBasicMaterial color={i === 0 ? "#0d1018" : "#0a0c13"} />
          </mesh>

          {/* The gold rim at each step edge - the dais's only light source. */}
          <mesh position={[0, tier.height / 2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[tier.radius, 0.008, 12, 128]} />
            <meshBasicMaterial
              color={i === 0 ? GOLD_BRIGHT : GOLD}
              transparent
              opacity={0.75 - i * 0.13}
              blending={THREE.AdditiveBlending}
              depthWrite={false}
            />
          </mesh>
        </group>
      ))}

      {/* Where the ball meets the dais: a warm pool of contact light.
          Textured with the soft radial sprite - an untextured circle renders
          as a flat opaque gold plate, which is exactly what it looked like. */}
      <mesh ref={core} position={[0, RING_LOW + 0.01, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <planeGeometry args={[3.4, 3.4]} />
        <meshBasicMaterial
          map={softDotTexture()}
          color={GOLD}
          transparent
          opacity={0.5}
          depthWrite={false}
          blending={THREE.AdditiveBlending}
        />
      </mesh>

      {/* A plain dark floor.
          Deliberately NOT MeshReflectorMaterial: that renders the entire scene
          a second time into a 1024px target every frame, which was the single
          largest cost here and the main source of the stutter. The fog and
          vignette carry the depth instead. */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, RING_LOW - 0.75, 0]}>
        <planeGeometry args={[40, 40]} />
        <meshBasicMaterial color="#04050a" />
      </mesh>
    </group>
  );
}
