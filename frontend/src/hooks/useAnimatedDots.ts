import { useState, useEffect } from 'react';

const PATTERNS = ['.', '..', '...', '..', '.'];

export function useAnimatedDots(active: boolean): string {
  const [index, setIndex] = useState(0);

  useEffect(() => {
    if (!active) {
      setIndex(0);
      return;
    }
    const id = setInterval(() => {
      setIndex((i) => (i + 1) % PATTERNS.length);
    }, 400);
    return () => clearInterval(id);
  }, [active]);

  return active ? PATTERNS[index] : '';
}
