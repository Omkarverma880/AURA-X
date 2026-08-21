import { useMemo } from "react";
import * as THREE from "three";

/**
 * The glass ball the ring encircles.
 *
 * Real glass (`meshPhysicalMaterial` with transmission) renders the scene into
 * a separate target every frame, which is far too expensive for a hero that
 * also carries a particle system and bloom. This gets the same read for
 * almost nothing: a Fresnel term, so the sphere is invisible where it faces
 * the camera and glows where it turns away - which is exactly how a clear
 * glass ball behaves, and what makes it read as a volume rather than a disc.
 *
 * Additive and depth-write-free, so the starfield still shows through it.
 */
export function AuraGlassSphere({ radius = 2.42 }: { radius?: number }) {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.FrontSide,
        uniforms: {
          uRim: { value: new THREE.Color("#ffd9a1") },
          uCore: { value: new THREE.Color("#122033") },
        },
        vertexShader: /* glsl */ `
          varying vec3 vNormal;
          varying vec3 vView;
          void main() {
            vec4 viewPosition = modelViewMatrix * vec4(position, 1.0);
            vNormal = normalize(normalMatrix * normal);
            vView = normalize(-viewPosition.xyz);
            gl_Position = projectionMatrix * viewPosition;
          }
        `,
        fragmentShader: /* glsl */ `
          uniform vec3 uRim;
          uniform vec3 uCore;
          varying vec3 vNormal;
          varying vec3 vView;

          void main() {
            // 0 facing the camera, 1 at the silhouette.
            float fresnel = 1.0 - clamp(dot(normalize(vNormal), normalize(vView)), 0.0, 1.0);

            // A high exponent keeps the body of the sphere almost perfectly
            // clear and concentrates the light into a thin edge.
            float rim = pow(fresnel, 4.5);
            float body = pow(fresnel, 1.6) * 0.09;

            vec3 colour = uCore * body + uRim * rim * 0.85;
            float alpha = clamp(body + rim * 0.9, 0.0, 1.0);

            gl_FragColor = vec4(colour, alpha);
          }
        `,
      }),
    [],
  );

  return (
    <mesh material={material}>
      <sphereGeometry args={[radius, 64, 48]} />
    </mesh>
  );
}
