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
export function AuraGlassSphere({ radius = 2.55 }: { radius?: number }) {
  const material = useMemo(
    () =>
      new THREE.ShaderMaterial({
        transparent: true,
        depthWrite: false,
        blending: THREE.AdditiveBlending,
        side: THREE.FrontSide,
        uniforms: {
          uRim: { value: new THREE.Color("#ffd9a1") },
          uCore: { value: new THREE.Color("#16233a") },
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

            // A low exponent spreads the highlight into a broad glassy
            // sheen. A sharp one drew a hard edge that read as a *second*
            // circle just inside the gold ring, which is exactly the effect
            // we do not want - there is one sphere, so one silhouette.
            float rim = pow(fresnel, 2.2);
            float sheen = pow(fresnel, 1.1) * 0.16;

            vec3 colour = uCore * sheen + uRim * rim * 0.34;
            float alpha = clamp(sheen + rim * 0.4, 0.0, 1.0);

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
