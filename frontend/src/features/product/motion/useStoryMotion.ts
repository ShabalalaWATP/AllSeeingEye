/**
 * Whether the story may move. The device's reduced-motion request, a signed-in
 * account's saved preference and the brand pause control (the same choice the
 * sign-in eye honours) all hold every scene in its final, readable state.
 */
import { createContext, useContext } from 'react';

import { useMotionPause } from '@/components/brand/useMotionPause';
import { usePageVisible, useReducedMotion } from '@/components/brand/useMotionPreferences';

export interface StoryMotion {
  /** No pinning, parallax, count-ups or animation: every scene shows its end state. */
  still: boolean;
  /** Continuous loops (globe spin, flames) should stop, for example in a hidden tab. */
  idle: boolean;
}

export function useStoryMotionSource(): StoryMotion {
  const reduced = useReducedMotion();
  const { chosenPause } = useMotionPause();
  const visible = usePageVisible();
  const still = reduced || chosenPause;
  return { still, idle: still || !visible };
}

export const StoryMotionContext = createContext<StoryMotion>({ still: true, idle: true });

export function useStoryMotion(): StoryMotion {
  return useContext(StoryMotionContext);
}
