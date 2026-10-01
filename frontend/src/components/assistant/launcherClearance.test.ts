import { expect, it } from 'vitest';

import {
  LAUNCHER_CLEARANCE_PX,
  LAUNCHER_SCROLL_MARGIN,
  LAUNCHER_SCROLL_PADDING,
} from './launcherClearance';
import { LAUNCHER_HEIGHT, LAUNCHER_HOME_BOTTOM } from './useAssistantPosition';

it('keeps scroll clearance at least as tall as the launcher footprint at its home position', () => {
  expect(LAUNCHER_HEIGHT + LAUNCHER_HOME_BOTTOM).toBeLessThanOrEqual(LAUNCHER_CLEARANCE_PX);
  // Tailwind spacing is 0.25rem (4px) per step: scroll-pb-28 and scroll-mb-28 are 112px.
  expect(LAUNCHER_SCROLL_PADDING).toBe(`scroll-pb-${LAUNCHER_CLEARANCE_PX / 4}`);
  expect(LAUNCHER_SCROLL_MARGIN).toBe(`[&_*]:scroll-mb-${LAUNCHER_CLEARANCE_PX / 4}`);
});
