import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Stars } from "@react-three/drei";
import * as THREE from "three";


import { AURA_BUDGET, type AuraTier } from "./useAuraCapabilities";

/**
 * Ambient depth: a starfield, a warm dust trail, and a cool cosmic haze far
 * behind the orb.
 *
 * No drei `Sparkles` anywhere in this scene, deliberately. Its jitter reads
 * as twitchy rather than cinematic, and this drei version also mis-sizes the
 * colour buffer when `color` is a hex/THREE.Color - a third such instance
 * reproducibly blanked the whole canvas. Everything here is hand-rolled
 * THREE.Points, which sidesteps both problems.
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

      {/* Energy trails sweeping in from both sides, the way a long exposure
          catches something orbiting. */}
      <GoldSwirl
        count={tier === "high" ? 520 : 180}
        position={[-3.6, -0.5, -1]}
        rotation={[0.2, 0.35, 0.5]}
        radius={3.6}
        size={0.022}
        opacity={0.7}
      />
      <GoldSwirl
        count={tier === "high" ? 320 : 110}
        position={[4.1, 0.4, -2.2]}
        rotation={[-0.15, -0.4, -2.5]}
        radius={3.1}
        size={0.018}
        opacity={0.6}
      />

      <CosmicHaze count={tier === "high" ? 320 : 110} />
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
        color="#7d95ff"
        size={0.07}
        sizeAttenuation
        transparent
        opacity={0.5}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/**
 * A spiral of gold dust, thinning as it unwinds outward.
 *
 * Points are laid out along a logarithmic spiral with a little jitter, so the
 * cloud reads as a trail of embers rather than a drawn curve. The whole group
 * rotates very slowly about its own axis - the particles never move relative
 * to each other, which keeps this to one matrix update per frame regardless
 * of particle count.
 */
function GoldSwirl({
  count,
  position,
  rotation,
  radius,
  size,
  opacity,
}: {
  count: number;
  position: [number, number, number];
  rotation: [number, number, number];
  radius: number;
  size: number;
  opacity: number;
}) {
  const points = useRef<THREE.Points>(null);

  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3);
    const turns = 2.4;

    for (let i = 0; i < count; i += 1) {
      // Bias t toward the outer end so the trail is dense where it leaves the
      // ring and sparse where it dissipates.
      const t = Math.sqrt(i / count);
      const angle = t * Math.PI * 2 * turns;
      const r = t * radius;
      // Jitter grows with radius, so the tail frays while the head stays tight.
      const spread = 0.06 + t * 0.5;

      positions[i * 3] = Math.cos(angle) * r + (Math.random() - 0.5) * spread;
      positions[i * 3 + 1] = Math.sin(angle) * r * 0.55 + (Math.random() - 0.5) * spread;
      positions[i * 3 + 2] = (Math.random() - 0.5) * spread * 1.6;
    }

    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    return geo;
  }, [count, radius]);

  useFrame((state) => {
    if (!points.current) return;
    points.current.rotation.z = rotation[2] + state.clock.getElapsedTime() * 0.012;
  });

  return (
    <points ref={points} geometry={geometry} position={position} rotation={rotation}>
      <pointsMaterial
        color="#ffc978"
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
