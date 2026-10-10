import { Link, useNavigate } from 'react-router';

import { Button } from '@/components/ui/Button';
import type { Activity, DayBucket } from '@/lib/api/trackers';
import { useEventsStore } from '@/stores/events';

/** Activity this week against the week before, with a plain-words trend. */
export function ActivityCells({ activity }: { activity: Activity }) {
  const trend =
    activity.trend === null
      ? 'no baseline'
      : activity.trend >= 1.5
        ? 'rising'
        : activity.trend <= 0.67
          ? 'falling'
          : 'steady';
  return (
    <span className="font-mono text-xs">
      {activity.last_24h} / 24 h · {activity.last_7d} / 7 d ·{' '}
      <span
        className={
          trend === 'rising' ? 'text-critical' : trend === 'falling' ? 'text-good' : 'text-muted'
        }
      >
        {trend}
      </span>
    </span>
  );
}

/** A day whose worst event reaches this normalised severity is drawn as high severity. */
const HIGH_SEVERITY = 0.85;

const isHigh = (bucket: DayBucket) => (bucket.max_severity ?? 0) >= HIGH_SEVERITY;

function dayText(bucket: DayBucket): string {
  const events = `${String(bucket.count)} ${bucket.count === 1 ? 'event' : 'events'}`;
  return `${bucket.day}: ${events}${isHigh(bucket) ? ', high severity' : ''}`;
}

/** A dot above the bar, so high severity never relies on colour alone. */
function SeverityMarker() {
  return (
    <span
      data-severity-marker=""
      aria-hidden="true"
      className="absolute -top-2 left-1/2 size-1.5 -translate-x-1/2 rounded-full bg-text"
    />
  );
}

/** Fourteen daily bars: the height follows the count; high-severity days are red and marked. */
export function Timeline({ buckets, label }: { buckets: readonly DayBucket[]; label: string }) {
  const most = Math.max(1, ...buckets.map((bucket) => bucket.count));
  return (
    <div className="flex flex-col gap-2">
      <div
        role="img"
        aria-label={`${label}: ${buckets.map(dayText).join('; ')}`}
        className="flex h-18 items-end gap-1 pt-2"
      >
        {buckets.map((bucket) => (
          <div
            key={bucket.day}
            title={dayText(bucket)}
            data-severity={isHigh(bucket) ? 'high' : undefined}
            className={`relative flex-1 rounded-sm ${isHigh(bucket) ? 'bg-critical' : 'bg-ember/70'}`}
            style={{ height: `${String(Math.max(4, Math.round((bucket.count / most) * 100)))}%` }}
          >
            {isHigh(bucket) && <SeverityMarker />}
          </div>
        ))}
      </div>
      <ul
        aria-label={`${label} legend`}
        className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted"
      >
        <li className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="h-3 w-2 rounded-sm bg-ember/70" />
          Events per day
        </li>
        <li className="inline-flex items-center gap-2">
          <span aria-hidden="true" className="relative mt-2 h-3 w-2 rounded-sm bg-critical">
            <SeverityMarker />
          </span>
          High severity ({String(HIGH_SEVERITY)} / 1 or above)
        </li>
      </ul>
    </div>
  );
}

/** Scope the globe to a nation and go there. */
export function ShowOnGlobe({ country }: { country: string | null }) {
  const navigate = useNavigate();
  const setCountry = useEventsStore((state) => state.setCountry);
  return (
    <Button
      variant="secondary"
      onClick={() => {
        setCountry(country);
        void navigate('/');
      }}
    >
      Show on globe
    </Button>
  );
}

export function BackToTrackers() {
  return (
    <Link to="/trackers" className="text-xs text-muted hover:underline">
      All trackers
    </Link>
  );
}
