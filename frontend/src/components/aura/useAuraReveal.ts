import { useEffect, useRef } from "react";

/**
 * Reveal-on-scroll, driven by one IntersectionObserver rather than a scroll
 * handler.
 *
 * Attach the returned ref to a container; every descendant carrying
 * `.aura-reveal` gets `.is-visible` as it enters the viewport, and is then
 * unobserved - the reveal is a one-way door, so nothing re-animates when the
 * user scrolls back up.
 *
 * `.aura-reveal` starts at opacity 0, which makes a missed observer callback
 * a *content-loss* bug rather than a missing flourish - the element simply
 * never appears. That is not hypothetical: on first paint the observer's
 * initial delivery can be batched across frames, and elements already on
 * screen were observed to stay hidden indefinitely. So anything within the
 * viewport at mount is revealed synchronously from its own geometry, and the
 * observer only handles what genuinely starts below the fold.
 *
 * The CSS honours prefers-reduced-motion by rendering `.aura-reveal` fully
 * visible with no transition, so this hook needs no guard of its own.
 */
export function useAuraReveal<T extends HTMLElement = HTMLDivElement>() {
  const containerRef = useRef<T>(null);

  useEffect(() => {
    const root = containerRef.current;
    if (!root) return;

    const targets = Array.from(root.querySelectorAll<HTMLElement>(".aura-reveal"));
    if (targets.length === 0) return;

    const reveal = (el: Element) => el.classList.add("is-visible");

    // No IntersectionObserver (very old browsers): show everything rather
    // than leaving the page permanently blank.
    if (typeof IntersectionObserver === "undefined") {
      targets.forEach(reveal);
      return;
    }

    const viewportHeight = window.innerHeight;
    const pending: HTMLElement[] = [];

    for (const el of targets) {
      const box = el.getBoundingClientRect();
      const onScreen = box.top < viewportHeight && box.bottom > 0;
      if (onScreen) reveal(el);
      else pending.push(el);
    }

    if (pending.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          reveal(entry.target);
          observer.unobserve(entry.target);
        });
      },
      // Fire a little before the element is fully on screen, so the motion
      // has finished by the time it is centred.
      { rootMargin: "0px 0px -12% 0px", threshold: 0.15 },
    );

    pending.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return containerRef;
}
