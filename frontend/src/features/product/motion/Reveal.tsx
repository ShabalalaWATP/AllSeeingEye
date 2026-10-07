/**
 * Content that rises into place the first time it enters the viewport. The text is
 * always in the document; only its transform and opacity change, and a still story
 * (or a browser without IntersectionObserver) shows it immediately.
 */
import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type ElementType,
  type ReactNode,
} from 'react';

import { useStoryMotion } from './useStoryMotion';

export interface RevealProps {
  as?: ElementType;
  /** Stagger position; each step delays the entrance by 70 ms. */
  order?: number;
  className?: string;
  children: ReactNode;
}

export function Reveal({ as: Tag = 'div', order = 0, className = '', children }: RevealProps) {
  const { still } = useStoryMotion();
  const ref = useRef<HTMLElement>(null);
  const [seen, setSeen] = useState(false);
  const observable = typeof IntersectionObserver === 'function';

  useEffect(() => {
    const element = ref.current;
    if (still || seen || element === null || !observable) return undefined;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setSeen(true);
          observer.disconnect();
        }
      },
      { rootMargin: '0px 0px -8% 0px' },
    );
    observer.observe(element);
    return () => observer.disconnect();
  }, [still, seen, observable]);

  const style = { '--reveal-order': order } as CSSProperties;
  return (
    <Tag
      ref={ref}
      className={`story-reveal ${className}`}
      data-shown={still || seen || !observable ? 'true' : 'false'}
      style={style}
    >
      {children}
    </Tag>
  );
}
