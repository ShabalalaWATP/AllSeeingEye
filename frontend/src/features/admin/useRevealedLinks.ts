import { useCallback, useRef, useState } from 'react';

export interface RevealedLink {
  key: number;
  title: string;
  link: string;
  expiresAt: string;
}

export interface RevealedLinks {
  links: RevealedLink[];
  reveal: (entry: Omit<RevealedLink, 'key'>) => void;
  dismiss: (key: number) => void;
}

/**
 * Keeps every one-time link revealed on this page until the administrator dismisses it,
 * so a later approval or reset does not overwrite a link that has not been copied yet.
 * A newer link with the same title (the same account and purpose) replaces the older one.
 */
export function useRevealedLinks(): RevealedLinks {
  const [links, setLinks] = useState<RevealedLink[]>([]);
  const next = useRef(0);

  const reveal = useCallback((entry: Omit<RevealedLink, 'key'>) => {
    next.current += 1;
    const key = next.current;
    setLinks((current) => [
      { ...entry, key },
      ...current.filter((item) => item.title !== entry.title),
    ]);
  }, []);

  const dismiss = useCallback((key: number) => {
    setLinks((current) => current.filter((item) => item.key !== key));
  }, []);

  return { links, reveal, dismiss };
}
