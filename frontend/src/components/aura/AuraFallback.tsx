/**
 * The Aura X orb without WebGL.
 *
 * Shown when the device has no WebGL context, or when the visitor has asked
 * their system for reduced motion. It is not a placeholder or an apology - it
 * is the same composition (gold ring, dark interior, warm pool of light on a
 * dais, scattered stars) rendered in CSS, so those visitors still arrive
 * somewhere that looks like Aura X.
 *
 * Every animation here is wrapped in a reduced-motion guard, so the
 * reduced-motion path renders the scene completely still.
 */
export function AuraFallback({ animated = true }: { animated?: boolean }) {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden bg-[#050507]">
      {/* Star field: a few fixed radial gradients, no DOM nodes per star. */}
      <div
        className="absolute inset-0 opacity-70"
        style={{
          backgroundImage: [
            "radial-gradient(1px 1px at 12% 22%, rgba(255,255,255,0.55) 50%, transparent 50%)",
            "radial-gradient(1px 1px at 78% 14%, rgba(255,255,255,0.4) 50%, transparent 50%)",
            "radial-gradient(1px 1px at 34% 68%, rgba(255,255,255,0.35) 50%, transparent 50%)",
            "radial-gradient(1.5px 1.5px at 63% 44%, rgba(255,255,255,0.3) 50%, transparent 50%)",
            "radial-gradient(1px 1px at 88% 72%, rgba(255,255,255,0.4) 50%, transparent 50%)",
            "radial-gradient(1px 1px at 22% 86%, rgba(255,255,255,0.28) 50%, transparent 50%)",
            "radial-gradient(1px 1px at 51% 8%, rgba(255,255,255,0.32) 50%, transparent 50%)",
          ].join(","),
        }}
      />

      {/* Distant cool haze. */}
      <div
        className="absolute right-[-10%] top-1/4 h-[42rem] w-[42rem] rounded-full opacity-25 blur-3xl"
        style={{ background: "radial-gradient(circle, #5c7cfa 0%, transparent 62%)" }}
      />

      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-[56%]">
        {/* Outer bloom. */}
        <div
          className="absolute left-1/2 top-1/2 h-[34rem] w-[34rem] -translate-x-1/2 -translate-y-1/2 rounded-full opacity-40 blur-3xl"
          style={{ background: "radial-gradient(circle, rgba(232,168,60,0.55) 0%, transparent 60%)" }}
        />

        {/* The ring, squashed into perspective to match the 3D camera. */}
        <div
          className={`relative h-[19rem] w-[19rem] rounded-full border border-[#e8a83c]/70 sm:h-[26rem] sm:w-[26rem] ${
            animated ? "aura-fallback-spin" : ""
          }`}
          style={{
            transform: "rotateX(62deg)",
            boxShadow:
              "0 0 40px rgba(232,168,60,0.5), inset 0 0 60px rgba(232,168,60,0.22)",
            background:
              "radial-gradient(circle, rgba(5,6,10,0.85) 55%, rgba(232,168,60,0.10) 100%)",
          }}
        >
          {/* A brighter arc, so the ring reads as lit rather than drawn. */}
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background:
                "conic-gradient(from 210deg, transparent 0deg, rgba(255,213,128,0.85) 55deg, transparent 130deg)",
              WebkitMask: "radial-gradient(circle, transparent 96%, #000 97%)",
              mask: "radial-gradient(circle, transparent 96%, #000 97%)",
            }}
          />
        </div>

        {/* Warm pool of light on the dais below. */}
        <div
          className="absolute left-1/2 top-[86%] h-24 w-[22rem] -translate-x-1/2 rounded-[50%] opacity-70 blur-2xl sm:w-[30rem]"
          style={{ background: "radial-gradient(ellipse, rgba(255,213,128,0.6) 0%, transparent 70%)" }}
        />
      </div>

      {/* Grounding vignette, matching the WebGL scene's post-processing. */}
      <div
        className="absolute inset-0"
        style={{ background: "radial-gradient(ellipse at center, transparent 40%, #050507 92%)" }}
      />
    </div>
  );
}
