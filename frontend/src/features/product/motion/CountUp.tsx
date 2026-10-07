/**
 * A number that counts up the first time it scrolls into view. Screen readers always
 * get the final value; a still story, or a browser without IntersectionObserver,
 * shows it straight away.
 */
import { useEffect, useRef, useState } from 'react';

import { useStoryMotion } from './useStoryMotion';

const DURATION_MS = 900;

export interface CountUpProps {
  value: number;
  suffix?: string;
}

function easeOut(t: number): number {
  return 1 - (1 - t) ** 3;
}

export function CountUp({ value, suffix = '' }: CountUpProps) {
  const { still } = useStoryMotion();
  const ref = useRef<HTMLSpanElement>(null);
  const [counted, setCounted] = useState<number | null>(null);
  const observable = typeof IntersectionObserver === 'function';
  const settled = still || !observable;
  const shown = settled ? value : (counted ?? 0);

  useEffect(() => {
    const element = ref.current;
    if (settled || element === null) return undefined;
    let frame = 0;
    const run = () => {
      const started = performance.now();
      const tick = (now: number) => {
        const t = Math.min(1, (now - started) / DURATION_MS);
        setCounted(Math.round(value * easeOut(t)));
        if (t < 1) frame = requestAnimationFrame(tick);
      };
      frame = requestAnimationFrame(tick);
    };
    const observer = new IntersectionObserver((entries) => {
      if (!entries.some((entry) => entry.isIntersecting)) return;
      observer.disconnect();
      run();
    });
    observer.observe(element);
    return () => {
      observer.disconnect();
      cancelAnimationFrame(frame);
    };
  }, [value, settled]);

  const text = `${value.toLocaleString('en-GB')}${suffix}`;
  return (
    <span ref={ref}>
      <span aria-hidden="true">
        {shown.toLocaleString('en-GB')}
        {suffix}
      </span>
      <span className="sr-only">{text}</span>
    </span>
  );
}
