import { useState } from 'react';

/**
 * A consent that applies to one exact plan. Any change of `key` withdraws it, and it
 * stays withdrawn even if the reader later restores the earlier values.
 */
export function useKeyedConsent(key: string): readonly [boolean, (value: boolean) => void] {
  const [consent, setConsent] = useState(false);
  const [givenFor, setGivenFor] = useState(key);
  if (givenFor !== key) {
    setGivenFor(key);
    setConsent(false);
  }
  return [consent && givenFor === key, setConsent] as const;
}
