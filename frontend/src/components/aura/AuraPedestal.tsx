import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { MeshReflectorMaterial } from "@react-three/drei";
import * as THREE from "three";

import { GOLD, GOLD_BRIGHT } from "./AuraOrb";

/**
 * The metallic dais the orb floats above: concentric rings of decreasing
 * presence, lit from a single warm source at their centre.
 */
export function AuraPedestal({ reflector }: { reflector: boolean }) {
  const halo = useRef<THREE.Mesh>(null);

  const rings = useMemo(
    () => [
      { radius: 1.9, height: 0.06, y: -1.55, opacity: 0.9 },
      { radius: 2.3, height: 0.045, y: -1.65, opacity: 0.6 },
      { radius: 2.7, height: 0.03, y: -1.73, opacity: 0.35 },
      { radius: 3.15, height: 0.02, y: -1.8, opacity: 0.18 },
    ],
    [],
  );

  useFrame((state) => {
    if (!halo.current) return;
    // A slow tide in the base glow - the only thing on screen that pulses,
    // and it takes eleven seconds to do it once.
    const t = state.clock.getElapsedTime();
    const material = halo.current.material as THREE.MeshBasicMaterial;
    material.opacity = 0.22 + Math.sin(t * 0.57) * 0.06;
  });

  return (
    <group>
      {rings.map((ring, i) => (
        <mesh key={i} position={[0, ring.y, 0]}>
          <cylinderGeometry args={[ring.radius, ring.radius, ring.height, 64]} />
          <meshStandardMaterial
            color="#0c0c10"
            emissive={GOLD}
            emissiveIntensity={0.18}
            roughness={0.35}
            metalness={0.85}
            transparent
            opacity={ring.opacity}
          />
        </mesh>
      ))}

      {/* Volumetric warmth pooling at the base. */}
      <mesh ref={halo} position={[0, -1.5, 0.02]}>
        <circleGeometry args={[2.4, 48]} />
        <meshBasicMaterial color={GOLD} transparent opacity={0.24} />
      </mesh>

      <pointLight position={[0, -1.5, 0]} color={GOLD_BRIGHT} intensity={4.5} distance={4.5} />
      <mesh position={[0, -1.5, 0]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshBasicMaterial color={GOLD_BRIGHT} />
      </mesh>

      {reflector ? (
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.86, 0]}>
          <planeGeometry args={[40, 40]} />
          <MeshReflectorMaterial
            blur={[300, 80]}
            resolution={1024}
            mixBlur={1}
            mixStrength={35}
            roughness={0.9}
            depthScale={1}
            minDepthThreshold={0.85}
            color="#030304"
            metalness={0.7}
            mirror={0.3}
          />
        </mesh>
      ) : (
        // The reflector renders the scene a second time into a render target,
        // which is the single most expensive thing here. Low-tier devices get
        // a plain dark floor instead - the vignette and fog carry the depth.
        <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.86, 0]}>
          <planeGeometry args={[40, 40]} />
          <meshStandardMaterial color="#050508" roughness={0.8} metalness={0.4} />
        </mesh>
      )}
    </group>
  );
}
