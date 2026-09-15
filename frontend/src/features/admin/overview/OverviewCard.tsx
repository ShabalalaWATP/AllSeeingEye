import type { ReactNode } from 'react';
import { Link } from 'react-router';

import { AdminIcon, type AdminGlyph } from '@/components/admin/AdminIcon';
import { Button } from '@/components/ui/Button';
import type { ApiError } from '@/lib/api/errors';
import { describeError } from '@/lib/api/errors';

export interface CardResource<T> {
  data: T | null;
  error: ApiError | null;
  loading: boolean;
  reload: () => Promise<void>;
}

/**
 * One overview tile. The title links to the page that owns the data; loading,
 * failure and permission states are handled here so every tile behaves alike.
 */
export function OverviewCard<T>({
  title,
  to,
  icon,
  resource,
  related,
  className = '',
  children,
}: {
  title: string;
  to: string;
  icon: AdminGlyph;
  resource: CardResource<T>;
  /** A second destination that stays reachable whatever state the data is in. */
  related?: { to: string; label: string };
  className?: string;
  children: (data: T) => ReactNode;
}) {
  const { data, error, loading, reload } = resource;
  return (
    <article
      aria-label={title}
      aria-busy={loading && data === null}
      className={`admin-rise group/card flex min-w-0 flex-col rounded-card border border-line/80 bg-surface/70 transition-colors hover:border-line ${className}`}
    >
      <header className="flex items-center justify-between gap-3 px-4 pt-4 sm:px-5">
        <h2 className="min-w-0 text-sm font-semibold">
          <Link
            to={to}
            className="group/link inline-flex min-h-8 items-center gap-2.5 rounded-md hover:text-ember"
          >
            <span className="flex size-8 items-center justify-center rounded-lg border border-line/80 bg-surface-2 text-ember">
              <AdminIcon name={icon} size={16} />
            </span>
            <span className="truncate">{title}</span>
            <AdminIcon
              name="arrow"
              size={14}
              className="text-muted transition-transform group-hover/link:translate-x-0.5 group-hover/link:text-ember"
            />
          </Link>
        </h2>
        {related === undefined ? null : (
          <Link
            to={related.to}
            className="inline-flex min-h-8 shrink-0 items-center rounded-md border border-line/80 px-2.5 text-xs font-medium text-muted hover:border-ember/50 hover:text-text"
          >
            {related.label}
          </Link>
        )}
      </header>
      <div className="flex min-w-0 flex-1 flex-col px-4 pt-3 pb-4 sm:px-5">
        {error !== null ? (
          <CardFailure error={error} title={title} busy={loading} onRetry={() => void reload()} />
        ) : data === null ? (
          <CardSkeleton label={`Loading ${title.toLowerCase()}`} />
        ) : (
          children(data)
        )}
      </div>
    </article>
  );
}

function CardSkeleton({ label }: { label: string }) {
  return (
    <div role="status" className="space-y-3">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true" className="admin-skeleton h-8 w-20 rounded-md" />
      <div aria-hidden="true" className="admin-skeleton h-3 w-full rounded" />
      <div aria-hidden="true" className="admin-skeleton h-3 w-2/3 rounded" />
    </div>
  );
}

function CardFailure({
  error,
  title,
  busy,
  onRetry,
}: {
  error: ApiError;
  title: string;
  busy: boolean;
  onRetry: () => void;
}) {
  if (error.status === 401 || error.status === 403) {
    return (
      <div role="status" className="flex items-start gap-2 text-sm text-muted">
        <AdminIcon name="security" size={16} className="mt-0.5 text-amber" />
        <p>
          This session cannot view {title.toLowerCase()} right now. Check your administrator
          verification in Security, then refresh.
        </p>
      </div>
    );
  }
  return (
    <div role="alert" className="space-y-2 text-sm">
      <p className="flex items-start gap-2">
        <AdminIcon name="alert" size={16} className="mt-0.5 text-critical" />
        <span>{describeError(error)}</span>
      </p>
      <Button
        variant="secondary"
        busy={busy}
        className="min-h-9"
        aria-label={`Retry ${title.toLowerCase()}`}
        onClick={onRetry}
      >
        <AdminIcon name="refresh" size={14} />
        Retry
      </Button>
    </div>
  );
}

/** A large figure with a short caption; the figure and caption read as one phrase. */
export function Figure({
  value,
  caption,
  tone = 'text-text',
}: {
  value: number | string;
  caption: string;
  tone?: string;
}) {
  return (
    <p className="flex items-baseline gap-2">
      <span className={`text-3xl font-semibold tracking-tight tabular-nums ${tone}`}>{value}</span>
      <span className="text-sm text-muted">{caption}</span>
    </p>
  );
}

export function StatList({ items }: { items: readonly { label: string; value: ReactNode }[] }) {
  return (
    <dl className="mt-4 grid grid-cols-2 items-end gap-x-4 gap-y-3 border-t border-line/60 pt-3 text-sm sm:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs leading-tight text-muted">{item.label}</dt>
          <dd className="mt-0.5 font-medium tabular-nums">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
