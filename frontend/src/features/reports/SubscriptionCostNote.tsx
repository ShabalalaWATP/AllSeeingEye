/** Make the cost consequence of cadence and depth visible while the choice is being made. */
import { describeRelativeCost, relativeCost, type Depth } from './subscriptionCost';
import type { Cadence } from './ScheduleTiming';

export function SubscriptionCostNote({
  cadence,
  depth,
  researching,
}: {
  cadence: Cadence;
  depth: Depth;
  researching: boolean;
}) {
  const multiple = relativeCost(cadence, depth, researching);
  const baseline = Math.abs(multiple - 1) < 0.05 && researching && depth === 'quick';
  return (
    <p className="text-xs leading-5 text-muted" role="note">
      <span className="font-medium text-text">Running cost:</span>{' '}
      {baseline
        ? 'this is the weekly Quick baseline, the cheapest useful recurring shape.'
        : `${describeRelativeCost(multiple)} the model work of a weekly Quick subscription.`}{' '}
      A daily Advanced subscription costs roughly twenty times a weekly Quick one, because it runs
      seven times as often and each run does far more model work. These are rough guides; your AI
      usage page shows what was actually recorded.
    </p>
  );
}
