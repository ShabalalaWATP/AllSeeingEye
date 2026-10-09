/**
 * Device-only motion for the public story. It never reads account preferences or
 * starts authenticated requests, including when a signed-in visitor opens the page.
 */
import { createContext, useContext } from 'react';

import { useProductMotionPause } from './useProductMotionPause';
import { usePageVisible } from '@/components/brand/useDeviceMotion';

export interface StoryMotion {
  /** No pinning, parallax, count-ups or animation: every scene shows its end state. */
  still: boolean;
  /** Continuous loops (globe spin, flames) should stop, for example in a hidden tab. */
  idle: boolean;
}

export function useStoryMotionSource(): StoryMotion {
  const { paused } = useProductMotionPause();
  const visible = usePageVisible();
  const still = paused;
  return { still, idle: still || !visible };
}

export const StoryMotionContext = createContext<StoryMotion>({ still: true, idle: true });

export function useStoryMotion(): StoryMotion {
  return useContext(StoryMotionContext);
}
