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
          trend === 'rising'
            ? 'text-critical'
            : trend === 'falling'
              ? 'text-emerald-300'
              : 'text-muted'
        }
      >
        {trend}
      </span>
    </span>
  );
}

/** Fourteen daily bars; the height follows the count and the colour the worst severity. */
export function Timeline({ buckets, label }: { buckets: readonly DayBucket[]; label: string }) {
  const most = Math.max(1, ...buckets.map((bucket) => bucket.count));
  return (
    <div
      role="img"
      aria-label={`${label}: ${buckets.map((bucket) => `${bucket.day} ${String(bucket.count)}`).join(', ')}`}
      className="flex h-16 items-end gap-1"
    >
      {buckets.map((bucket) => (
        <div
          key={bucket.day}
          title={`${bucket.day}: ${String(bucket.count)}`}
          className={`flex-1 rounded-sm ${
            (bucket.max_severity ?? 0) >= 0.85 ? 'bg-critical' : 'bg-ember/70'
          }`}
          style={{ height: `${String(Math.max(4, Math.round((bucket.count / most) * 100)))}%` }}
        />
      ))}
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
