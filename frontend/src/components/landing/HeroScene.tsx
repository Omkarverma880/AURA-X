import { Suspense, useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";

/**
 * The animated centrepiece: a glowing gold ring tilted in perspective,
 * hovering over a stepped dark pedestal, set against a starfield. Rendered
 * with react-three-fiber so the glow/bloom is real WebGL post-processing
 * rather than a CSS approximation - it is what makes the ring actually look
 * lit rather than just coloured.
 */

const GOLD = "#e8a83c";
const GOLD_BRIGHT = "#ffd580";

function GlowRing() {
  const groupRef = useRef<THREE.Group>(null);
  const { mouse } = useThree();

  useFrame((state) => {
    if (!groupRef.current) return;
    const t = state.clock.getElapsedTime();
    groupRef.current.rotation.z = t * 0.12;
    // Subtle parallax: the whole ring drifts slightly toward the cursor.
    groupRef.current.rotation.x = THREE.MathUtils.lerp(
      groupRef.current.rotation.x,
      0.5 + mouse.y * 0.06,
      0.04,
    );
    groupRef.current.rotation.y = THREE.MathUtils.lerp(
      groupRef.current.rotation.y,
      mouse.x * 0.1,
      0.04,
    );
  });

  return (
    <group ref={groupRef} rotation={[0.5, 0, 0]}>
      <mesh>
        <torusGeometry args={[2.6, 0.035, 32, 200]} />
        <meshStandardMaterial
          color={GOLD}
          emissive={GOLD_BRIGHT}
          emissiveIntensity={1.1}
          roughness={0.3}
          metalness={0.6}
        />
      </mesh>
      {/* A slightly larger, fainter echo ring gives the streaked "comet trail"
          look from the reference without needing a particle trail system. */}
      <mesh rotation={[0, 0, 0.4]}>
        <torusGeometry args={[2.63, 0.006, 16, 200, Math.PI * 1.15]} />
        <meshBasicMaterial color={GOLD_BRIGHT} transparent opacity={0.4} />
      </mesh>
    </group>
  );
}

function Pedestal() {
  const rings = useMemo(
    () => [
      { radius: 1.9, height: 0.06, y: -1.55, opacity: 0.9 },
      { radius: 2.3, height: 0.045, y: -1.65, opacity: 0.6 },
      { radius: 2.7, height: 0.03, y: -1.73, opacity: 0.35 },
    ],
    [],
  );

  return (
    <group>
      {rings.map((ring, i) => (
        <mesh key={i} position={[0, ring.y, 0]}>
          <cylinderGeometry args={[ring.radius, ring.radius, ring.height, 64]} />
          <meshStandardMaterial
            color="#0c0c10"
            emissive={GOLD}
            emissiveIntensity={0.15}
            roughness={0.4}
            metalness={0.8}
            transparent
            opacity={ring.opacity}
          />
        </mesh>
      ))}
      {/* The bright light source at the base, matching the reference's glow. */}
      <pointLight position={[0, -1.5, 0]} color={GOLD_BRIGHT} intensity={3.5} distance={4} />
      <mesh position={[0, -1.5, 0]}>
        <sphereGeometry args={[0.07, 16, 16]} />
        <meshBasicMaterial color={GOLD_BRIGHT} />
      </mesh>
    </group>
  );
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.06} />
      <pointLight position={[4, 3, 4]} intensity={0.15} color={GOLD} />
      <Stars radius={60} depth={40} count={2200} factor={2.4} saturation={0} fade speed={0.4} />
      <GlowRing />
      <Pedestal />
      <EffectComposer>
        <Bloom
          intensity={0.55}
          luminanceThreshold={0.35}
          luminanceSmoothing={0.25}
          mipmapBlur
        />
        <Vignette eskil={false} offset={0.2} darkness={1.1} />
      </EffectComposer>
    </>
  );
}

export function HeroScene() {
  return (
    <Canvas
      camera={{ position: [0, 0.4, 7], fov: 45 }}
      dpr={[1, 1.75]}
      gl={{ antialias: true, powerPreference: "high-performance" }}
      className="!absolute inset-0"
    >
      <color attach="background" args={["#050507"]} />
      <fog attach="fog" args={["#050507", 8, 16]} />
      <Suspense fallback={null}>
        <Scene />
      </Suspense>
    </Canvas>
  );
}
