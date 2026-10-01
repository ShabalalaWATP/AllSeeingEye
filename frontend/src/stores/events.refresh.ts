/** Bulk feeds invalidate snapshots; they must not create an endless download loop. */
import type { Category } from '@/lib/api/eventSchemas';

export const SNAPSHOT_REFRESH_MS = 10_000;
export const SNAPSHOT_COALESCE_MS = 1_000;
/** A failed soft refresh retries after 10, 20 and 40 seconds, then waits for a new hint. */
export const MAX_REFRESH_RETRIES = 3;

/** Every partition, or only the named categories. */
export type RefreshScope = 'all' | ReadonlySet<Category>;

export class SnapshotRefresh {
  private requested: 'all' | Set<Category> | null = null;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private startedAt = -Infinity;
  private delay = 0;

  constructor(private readonly reload: (scope: RefreshScope) => void) {}

  started(): void {
    this.cancel();
    this.startedAt = Date.now();
  }

  /** Coalesce a hint; partitions accumulate until one refresh covers them all. */
  request(loading: boolean, categories: readonly Category[] | null = null): void {
    if (categories === null || this.requested === 'all') this.requested = 'all';
    else this.requested = new Set([...(this.requested ?? []), ...categories]);
    if (!loading) this.finished();
  }

  /** Schedule another attempt at a failed soft refresh, backing off with each failure. */
  retry(scope: RefreshScope, attempt: number): void {
    this.delay = SNAPSHOT_REFRESH_MS * 2 ** (attempt - 1);
    this.request(false, scope === 'all' ? null : [...scope]);
  }

  finished(): void {
    if (this.requested === null || this.timer !== null) return;
    const delay = Math.max(
      SNAPSHOT_COALESCE_MS,
      SNAPSHOT_REFRESH_MS - (Date.now() - this.startedAt),
      this.delay,
    );
    this.delay = 0;
    this.timer = setTimeout(() => {
      this.timer = null;
      const scope = this.requested;
      if (scope !== null) this.reload(scope);
    }, delay);
  }

  cancel(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.requested = null;
    this.delay = 0;
  }
}
