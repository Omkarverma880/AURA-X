import * as THREE from "three";

/**
 * A soft round sprite for every particle in the scene.
 *
 * `PointsMaterial` draws each point as a hard-edged square by default, which
 * is why untextured particle fields read as digital noise - and why stray
 * background points showed up as visible blue squares. Mapping this radial
 * gradient onto them turns each one into a glowing dot with no edge at all,
 * which is the whole difference between "sparkles" and "light".
 *
 * Generated once and shared by every material - a 64px canvas costs nothing,
 * but creating one per shell would waste texture memory and uploads.
 */
let cached: THREE.Texture | null = null;

export function softDotTexture(): THREE.Texture {
  if (cached) return cached;

  const size = 64;
  const canvas = document.createElement("canvas");
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  if (!ctx) {
    // Canvas unavailable (very unusual). A null-ish texture still renders as
    // the default square rather than throwing.
    cached = new THREE.Texture();
    return cached;
  }

  const half = size / 2;
  const gradient = ctx.createRadialGradient(half, half, 0, half, half, half);
  // A steep falloff keeps a bright core while the halo fades to nothing well
  // before the sprite's edge, so overlapping points blend instead of tiling.
  gradient.addColorStop(0, "rgba(255,255,255,1)");
  gradient.addColorStop(0.25, "rgba(255,255,255,0.65)");
  gradient.addColorStop(0.55, "rgba(255,255,255,0.16)");
  gradient.addColorStop(1, "rgba(255,255,255,0)");

  ctx.fillStyle = gradient;
  ctx.fillRect(0, 0, size, size);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  cached = texture;
  return texture;
}
