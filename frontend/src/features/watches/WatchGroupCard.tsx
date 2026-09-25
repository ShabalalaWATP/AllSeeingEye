import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';

import type { WatchGroupState } from './useWatches';
import { countLabel } from './watchModel';

/** One kind of standing watch: what it is, how many there are and the latest few. */
export function WatchGroupCard({ group }: { group: WatchGroupState }) {
  const headingId = `watch-${group.kind}`;
  const name = group.title.toLowerCase();
  return (
    <li className="flex flex-col gap-3 rounded-card border border-line bg-surface p-4">
      <section aria-labelledby={headingId} className="flex flex-1 flex-col gap-3">
        <div className="flex items-baseline justify-between gap-3">
          <h2 id={headingId} className="text-base font-semibold">
            {group.title}
          </h2>
          {group.summary && (
            <p className="shrink-0 font-mono text-xs text-muted tabular-nums">
              {countLabel(group.summary)} total
            </p>
          )}
        </div>
        <p className="text-sm leading-6 text-muted">{group.explanation}</p>
        {group.loading && <LoadingNote label={`Loading ${name}`} />}
        {group.error && (
          <Alert tone="error">
            {describeError(group.error)}{' '}
            <Button variant="ghost" onClick={group.retry}>
              Retry {name}
            </Button>
          </Alert>
        )}
        {group.summary &&
          (group.summary.items.length === 0 ? (
            <p className="text-sm text-muted">{group.emptyText}</p>
          ) : (
            <ul aria-label={`Latest ${name}`} className="flex flex-col divide-y divide-line/60">
              {group.summary.items.map((item) => (
                <li key={item.id} className="py-2">
                  <Link to={item.to} className="text-sm font-medium text-text hover:underline">
                    {item.label}
                  </Link>
                  <p className="text-xs text-muted">{item.detail}</p>
                </li>
              ))}
            </ul>
          ))}
        <Link to={group.href} className="mt-auto w-fit text-sm text-ember hover:underline">
          {group.linkLabel}
        </Link>
      </section>
    </li>
  );
}
