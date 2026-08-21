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
 * `deps` matters when the revealed content is rendered conditionally. This
 * effect can only find elements that already exist, so on a page that shows a
 * skeleton first - the dashboard - it ran while the container was still null,
 * bailed out, and never set up an observer. The content then mounted at
 * opacity 0 and stayed invisible permanently, which reads as "the page never
 * finished loading". Pass whatever gates the render (the query result) so the
 * scan re-runs once the real content exists.
 *
 * The CSS honours prefers-reduced-motion by rendering `.aura-reveal` fully
 * visible with no transition, so this hook needs no guard of its own.
 */
export function useAuraReveal<T extends HTMLElement = HTMLDivElement>(
  deps: readonly unknown[] = [],
) {
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return containerRef;
}
