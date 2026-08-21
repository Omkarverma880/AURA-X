import { Suspense, useRef, useMemo } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Stars, Sparkles, MeshReflectorMaterial } from "@react-three/drei";
import { EffectComposer, Bloom, Vignette } from "@react-three/postprocessing";
import * as THREE from "three";

/**
 * The animated centrepiece: a glowing gold ring tilted in perspective,
 * hovering over a reflective dark pedestal, set against a starfield -
 * matching the reference mockup. Rendered with react-three-fiber so the
 * glow/bloom/reflections are real WebGL post-processing rather than a CSS
 * approximation.
 *
 * NOTE: a third, distant `<Sparkles color="...">` cluster (attempted for a
 * cool-toned nebula on one side) reproducibly blanked the entire canvas to
 * black in this environment - a real bug in this drei version's Sparkles
 * color-attribute sizing (it multiplies the buffer length by an extra
 * factor of 3 whenever `color` is a THREE.Color/hex/array). Two Sparkles
 * instances with an explicit `color` are confirmed stable; do not add a
 * third without pre-building the color buffer as a Float32Array yourself
 * (the `isFloat32Array(prop)` branch skips the buggy path entirely).
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
          emissiveIntensity={1.3}
          roughness={0.25}
          metalness={0.7}
        />
      </mesh>
      {/* Layered echo arcs of decreasing opacity/width trace a comet-trail
          streak around part of the ring, like the reference. */}
      <mesh rotation={[0, 0, 0.35]}>
        <torusGeometry args={[2.63, 0.009, 16, 200, Math.PI * 1.1]} />
        <meshBasicMaterial color={GOLD_BRIGHT} transparent opacity={0.45} />
      </mesh>
      <mesh rotation={[0, 0, 0.3]}>
        <torusGeometry args={[2.67, 0.004, 16, 200, Math.PI * 0.7]} />
        <meshBasicMaterial color="#fff2d6" transparent opacity={0.3} />
      </mesh>
      {/* Fine gold dust hugging the ring, giving the granular sparkle
          texture visible along the reference's arc. */}
      <Sparkles count={140} scale={[6, 6, 0.3]} size={2.2} speed={0.15} color={GOLD_BRIGHT} opacity={0.8} noise={0.4} />
    </group>
  );
}

function Pedestal() {
  const rings = useMemo(
    () => [
      { radius: 1.9, height: 0.06, y: -1.55, opacity: 0.9 },
      { radius: 2.3, height: 0.045, y: -1.65, opacity: 0.6 },
      { radius: 2.7, height: 0.03, y: -1.73, opacity: 0.35 },
      { radius: 3.15, height: 0.02, y: -1.8, opacity: 0.18 },
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
            emissiveIntensity={0.18}
            roughness={0.35}
            metalness={0.85}
            transparent
            opacity={ring.opacity}
          />
        </mesh>
      ))}
      {/* The bright light source at the base, matching the reference's glow. */}
      <pointLight position={[0, -1.5, 0]} color={GOLD_BRIGHT} intensity={4.5} distance={4.5} />
      <mesh position={[0, -1.5, 0]}>
        <sphereGeometry args={[0.08, 16, 16]} />
        <meshBasicMaterial color={GOLD_BRIGHT} />
      </mesh>
    </group>
  );
}

function ReflectiveFloor() {
  return (
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
  );
}

function Scene() {
  return (
    <>
      <ambientLight intensity={0.06} />
      <pointLight position={[4, 3, 4]} intensity={0.18} color={GOLD} />
      {/* Cool rim light from the right - hints at depth without the risk of
          a third Sparkles cluster (see file header). */}
      <pointLight position={[6, 2, -2]} intensity={0.3} color="#5c7cfa" />

      <Stars radius={70} depth={45} count={2800} factor={2.6} saturation={0} fade speed={0.35} />

      {/* Warm dust-trail drifting off to the left, echoing the reference's
          comet-tail spiral. */}
      <Sparkles count={220} scale={[9, 5, 4]} position={[-5, -0.5, -2]} size={1.6} speed={0.1} color={GOLD} opacity={0.55} noise={1.2} />

      <GlowRing />
      <Pedestal />
      <ReflectiveFloor />

      <EffectComposer>
        <Bloom intensity={0.6} luminanceThreshold={0.32} luminanceSmoothing={0.25} mipmapBlur />
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
      onCreated={(state) => {
        state.gl.toneMapping = THREE.ACESFilmicToneMapping;
        state.gl.toneMappingExposure = 1.15;
      }}
      className="!absolute inset-0"
    >
      <color attach="background" args={["#050507"]} />
      <fog attach="fog" args={["#050507", 8, 17]} />
      <Suspense fallback={null}>
        <Scene />
      </Suspense>
    </Canvas>
  );
}
