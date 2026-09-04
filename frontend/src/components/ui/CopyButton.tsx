import { useEffect, useState } from 'react';

import { Button } from './Button';

type CopyState = 'idle' | 'copied' | 'failed';

export interface CopyButtonProps {
  value: string;
  label?: string;
}

/** Copies `value` to the clipboard and confirms in the button text for a moment. */
export function CopyButton({ value, label = 'Copy link' }: CopyButtonProps) {
  const [state, setState] = useState<CopyState>('idle');

  useEffect(() => {
    if (state === 'idle') return;
    const timer = window.setTimeout(() => {
      setState('idle');
    }, 2000);
    return () => {
      window.clearTimeout(timer);
    };
  }, [state]);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setState('copied');
    } catch {
      setState('failed');
    }
  }

  const text = state === 'copied' ? 'Copied' : state === 'failed' ? 'Copy failed' : label;
  return (
    <Button variant="secondary" onClick={() => void copy()} aria-live="polite">
      {text}
    </Button>
  );
}
