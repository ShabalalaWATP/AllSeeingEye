/** Bulk feeds invalidate snapshots; they must not create an endless download loop. */
export const SNAPSHOT_REFRESH_MS = 10_000;
export const SNAPSHOT_COALESCE_MS = 1_000;

export class SnapshotRefresh {
  private requested = false;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private startedAt = -Infinity;

  constructor(private readonly reload: () => void) {}

  started(): void {
    this.cancel();
    this.startedAt = Date.now();
  }

  request(loading: boolean): void {
    this.requested = true;
    if (!loading) this.finished();
  }

  finished(): void {
    if (!this.requested || this.timer !== null) return;
    const delay = Math.max(
      SNAPSHOT_COALESCE_MS,
      SNAPSHOT_REFRESH_MS - (Date.now() - this.startedAt),
    );
    this.timer = setTimeout(() => {
      this.timer = null;
      if (this.requested) this.reload();
    }, delay);
  }

  cancel(): void {
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = null;
    this.requested = false;
  }
}
