import { useSyncExternalStore } from 'react';

// true כשה-media query מתקיים (למשל '(min-width: 1024px)'). בלי setState ב-effect.
export const useMediaQuery = (query) => useSyncExternalStore(
  (onChange) => {
    const mql = window.matchMedia(query);
    mql.addEventListener('change', onChange);
    return () => mql.removeEventListener('change', onChange);
  },
  () => window.matchMedia(query).matches,
  () => false,
);

export const useIsDesktop = () => useMediaQuery('(min-width: 1024px)');
