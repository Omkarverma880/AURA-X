import { useEffect, useRef } from "react";

/**
 * Reveal-on-scroll, done with one IntersectionObserver instead of a scroll
 * handler.
 *
 * Attach the returned ref to a container; every descendant carrying
 * `.aura-reveal` gets `.is-visible` as it enters the viewport, and is then
 * unobserved - the reveal is a one-way door, so nothing re-animates when the
 * user scrolls back up.
 *
 * The CSS honours prefers-reduced-motion by rendering `.aura-reveal` fully
 * visible with no transition, so this hook needs no guard of its own.
 */
export function useAuraReveal<T extends HTMLElement = HTMLDivElement>() {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const targets = root.querySelectorAll<HTMLElement>(".aura-reveal");
    if (targets.length === 0) return;

    // No IntersectionObserver (very old browsers): show everything rather
    // than leaving the page permanently blank.
    if (typeof IntersectionObserver === "undefined") {
      targets.forEach((el) => el.classList.add("is-visible"));
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.classList.add("is-visible");
          observer.unobserve(entry.target);
        });
      },
      // Fire a little before the element is fully on screen, so the motion
      // has finished by the time it is centred.
      { rootMargin: "0px 0px -12% 0px", threshold: 0.15 },
    );

    targets.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return containerRef;
}
