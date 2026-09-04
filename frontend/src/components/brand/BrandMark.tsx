/**
 * The small live brand mark: the React Bits Evil Eye at about 40 px with a
 * fixed pupil, capped at 24 frames per second, paused while the tab is hidden,
 * and effectively static (flames stopped, one frame per second) when the user
 * prefers reduced motion.
 */
import EvilEye from './EvilEye';
import { BRAND_GROUND, BRAND_NAME } from './tokens';
import { usePageVisible, useReducedMotion } from './useMotionPreferences';

export interface BrandMarkProps {
  size?: number;
}

export function BrandMark({ size = 40 }: BrandMarkProps) {
  const reducedMotion = useReducedMotion();
  const visible = usePageVisible();

  return (
    <div
      role="img"
      aria-label={BRAND_NAME}
      className="shrink-0 overflow-hidden rounded-full"
      style={{ width: size, height: size }}
    >
      <EvilEye
        pupilFollow={0}
        backgroundColor={BRAND_GROUND}
        maxFps={reducedMotion ? 1 : 24}
        flameSpeed={reducedMotion ? 0 : 1}
        paused={!visible}
      />
    </div>
  );
}
