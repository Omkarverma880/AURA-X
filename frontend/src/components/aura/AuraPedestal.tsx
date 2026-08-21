import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshReflectorMaterial } from "@react-three/drei";
import * as THREE from "three";

import { GOLD, GOLD_BRIGHT } from "./AuraOrb";

/**
 * The machined dais the orb floats above.
 *
 * Built as dark metal with thin gold rims, not gold plates. Emissive gold on
 * the tier *faces* makes the steps merge into one bright mass that reads as a
 * solid dome the moment bloom touches it - the warmth has to come from the
 * edges instead, which is also what gives the stepped, turned-metal look.
 *
 * Kept narrower than the ring so the orb still dominates the frame.
 */
export function AuraPedestal({ reflector }: { reflector: boolean }) {
  const core = useRef<THREE.Mesh>(null);

  const tiers = useMemo(
    () => [
      { radius: 1.55, height: 0.09, y: -1.5 },
      { radius: 1.95, height: 0.07, y: -1.61 },
      { radius: 2.4, height: 0.06, y: -1.71 },
      { radius: 2.9, height: 0.05, y: -1.8 },
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
          {/* Unlit on purpose.
              A lit metal here is unpredictable: the warm key light plus ACES
              tone mapping plus bloom kept returning a brass wash across the
              whole face no matter how the roughness/metalness were tuned. An
              unlit material cannot do that - the tiers are exactly this dark
              navy, always, and every bit of warmth on the dais comes from the
              rim rings and the core below. */}
          <mesh>
            <cylinderGeometry args={[tier.radius, tier.radius, tier.height, 72]} />
            <meshBasicMaterial color={i === 0 ? "#0d1018" : "#0a0c13"} />
          </mesh>

          {/* The gold rim catching light at each step edge - all of the dais's
              warmth comes from these, not from the faces. */}
          <mesh position={[0, tier.height / 2, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[tier.radius, 0.005, 12, 120]} />
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

      {/* The warm source at the centre of the dais. */}
      <pointLight position={[0, -1.4, 0]} color={GOLD_BRIGHT} intensity={0.22} distance={1.6} />
      <mesh ref={core} position={[0, -1.44, 0]}>
        <sphereGeometry args={[0.035, 16, 16]} />
        <meshBasicMaterial color={GOLD_BRIGHT} transparent opacity={0.9} />
      </mesh>

      {reflector ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.84, 0]}>
          <planeGeometry args={[40, 40]} />
          <MeshReflectorMaterial
            blur={[300, 80]}
            resolution={1024}
            mixBlur={1}
            mixStrength={10}
            roughness={0.9}
            depthScale={1}
            minDepthThreshold={0.85}
            color="#030304"
            metalness={0.7}
            mirror={0.25}
          />
        </mesh>
      ) : (
        // The reflector renders the scene a second time into a render target,
        // which is the single most expensive thing here. Low-tier devices get
        // a plain dark floor instead - fog and vignette carry the depth.
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.84, 0]}>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color="#050508" roughness={0.8} metalness={0.4} />
        </mesh>
      )}
    </group>
  );
}
