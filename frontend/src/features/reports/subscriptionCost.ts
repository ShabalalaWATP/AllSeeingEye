/**
 * Approximate model work of one subscription, relative to a weekly Quick subscription.
 *
 * Two things drive the bill: how often a subscription runs, and how much model work each
 * run does. Detailed and Advanced add challenge and devil's advocate passes on top of the
 * drafting passes a Quick run makes, so each run costs more as well as running more often.
 * These weights are deliberately rough: they are there to make the choice visible at
 * creation, not to predict an invoice. The AI usage pages show what was actually recorded.
 */
import type { Cadence } from './ScheduleTiming';

export type Depth = 'quick' | 'detailed' | 'advanced';

export const RUNS_PER_WEEK: Record<Cadence, number> = {
  daily: 7,
  weekdays: 5,
  weekly: 1,
  monthly: 12 / 52,
  quarterly: 4 / 52,
  semiannual: 2 / 52,
  annual: 1 / 52,
};

export const DEPTH_WEIGHT: Record<Depth, number> = {
  quick: 1,
  detailed: 2,
  advanced: 2.9,
};

/** A multiple of the weekly Quick baseline. Live-only runs do no research work. */
export function relativeCost(cadence: Cadence, depth: Depth, researching: boolean): number {
  return RUNS_PER_WEEK[cadence] * (researching ? DEPTH_WEIGHT[depth] : 0.6);
}

export function describeRelativeCost(multiple: number): string {
  if (multiple >= 10) return `about ${Math.round(multiple)} times`;
  if (multiple >= 1.5) return `about ${multiple.toFixed(1)} times`;
  if (multiple > 0.9 && multiple < 1.1) return 'about the same as';
  return `about ${multiple.toFixed(2)} times`;
}
