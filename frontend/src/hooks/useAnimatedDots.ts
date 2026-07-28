import { useState, useEffect } from 'react';

const PATTERNS = ['.', '..', '...', '..', '.'];

export function useAnimatedDots(active: boolean): string {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) return;
    // The interval is the only writer: it starts from whatever index the last
    // run left behind, and the `active ? ... : ''` return below hides that
    // leftover while inactive. Resetting the index here instead would be a
    // setState in the effect body, which cascades an extra render.
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % PATTERNS.length);
    }, 400);
    return () => clearInterval(id);
  }, [active]);

  return active ? PATTERNS[index] : '';
}
