import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import {
  fetchSubscriptionEditions,
  type SubscriptionEdition,
} from '@/lib/api/subscriptionEditions';
import {
  acceptSubscriptionBaseline,
  controlSubscriptionEdition,
  type EditionControl,
} from '@/lib/api/subscriptionControls';
import { formatUtc } from '@/lib/format';
import { SubscriptionActivity } from './SubscriptionActivity';

const PAGE_SIZE = 10;

function statusLabel(edition: SubscriptionEdition): string {
  if (edition.workflow === 'completed') {
    if (edition.report_quality === 'needs_review') return 'Needs review';
    if (edition.coverage !== 'complete_for_plan') return 'Partial coverage';
    return 'Ready';
  }
  const labels: Record<SubscriptionEdition['workflow'], string> = {
    pending: 'Waiting for capacity',
    queued: 'Queued',
    running: 'Running',
    retry_wait: 'Waiting to retry',
    paused: 'Paused',
    blocked: 'Blocked',
    completed: 'Ready',
    failed: 'Failed',
    cancelled: 'Cancelled',
    skipped: 'Skipped',
  };
  return labels[edition.workflow];
}

function editionLink(edition: SubscriptionEdition) {
  if (edition.report_id) {
    return (
      <Link className="text-ember underline" to={`/reports/${edition.report_id}`}>
        Read report
      </Link>
    );
  }
  if (edition.job_id) {
    return (
      <Link className="text-ember underline" to={`/research/jobs/${edition.job_id}`}>
        View progress
      </Link>
    );
  }
  if (edition.safe_reason === 'research_usage_limit')
    return <span className="text-muted">Not started</span>;
  return <span className="text-muted">Pending admission</span>;
}

function canAcceptBaseline(edition: SubscriptionEdition): boolean {
  return (
    edition.workflow === 'completed' &&
    !edition.accepted_as_baseline &&
    Boolean(edition.report_id && edition.version_id) &&
    (edition.report_quality === 'needs_review' || edition.coverage === 'partial')
  );
}

export function SubscriptionHistory({
  subscriptionId,
  canManage,
}: {
  subscriptionId: string;
  canManage: boolean;
}) {
  const [items, setItems] = useState<SubscriptionEdition[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [controlling, setControlling] = useState<string | null>(null);
  const [controlError, setControlError] = useState<string | null>(null);
  const [baselineConfirm, setBaselineConfirm] = useState<string | null>(null);
  const [baselineNotice, setBaselineNotice] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);

  const loadPage = useCallback(
    async (offset: number, replace: boolean) => {
      pending.current?.abort();
      const controller = new AbortController();
      pending.current = controller;
      setLoading(true);
      setError(null);
      try {
        const page = await fetchSubscriptionEditions(subscriptionId, offset, controller.signal);
        if (controller.signal.aborted) return;
        setItems((current) => (replace ? page.items : [...current, ...page.items]));
        setHasMore(page.items.length === PAGE_SIZE);
      } catch (cause) {
        if (!controller.signal.aborted) setError(describeError(cause));
      } finally {
        if (pending.current === controller) {
          pending.current = null;
          setLoading(false);
        }
      }
    },
    [subscriptionId],
  );

  useEffect(() => {
    let disposed = false;
    queueMicrotask(() => {
      if (!disposed) void loadPage(0, true);
    });
    return () => {
      disposed = true;
      pending.current?.abort();
    };
  }, [loadPage]);

  const control = async (edition: SubscriptionEdition, action: EditionControl) => {
    setControlling(edition.id);
    setControlError(null);
    try {
      const updated = await controlSubscriptionEdition(subscriptionId, edition.id, action);
      setItems((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      await loadPage(0, true);
    } catch (cause) {
      setControlError(describeError(cause));
    } finally {
      setControlling(null);
    }
  };

  const acceptBaseline = async (edition: SubscriptionEdition) => {
    setControlling(edition.id);
    setControlError(null);
    setBaselineNotice(null);
    try {
      await acceptSubscriptionBaseline(subscriptionId, edition.id);
      setBaselineConfirm(null);
      setBaselineNotice('Accepted for future comparisons. Unsearched intervals remain uncovered.');
      await loadPage(0, true);
    } catch (cause) {
      setControlError(describeError(cause));
    } finally {
      setControlling(null);
    }
  };

  return (
    <section
      aria-label="Subscription history"
      className="rounded-xl border border-line/70 bg-surface/80 p-4"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Edition history</h3>
          <p className="text-xs text-muted">
            Each scheduled run keeps its own status and report link.
          </p>
        </div>
        <Button variant="secondary" disabled={loading} onClick={() => void loadPage(0, true)}>
          Refresh
        </Button>
      </div>
      <SubscriptionActivity subscriptionId={subscriptionId} />
      {error && <Alert tone="error">{error}</Alert>}
      {controlError && <Alert tone="error">{controlError}</Alert>}
      {baselineNotice && (
        <p role="status" className="mb-3 text-xs text-good">
          {baselineNotice}
        </p>
      )}
      {loading && items.length === 0 && <LoadingNote label="Loading edition history" />}
      {!loading && !error && items.length === 0 && (
        <p className="text-sm text-muted">No editions have been scheduled yet.</p>
      )}
      {items.length > 0 && (
        <ul className="divide-y divide-line/60">
          {items.map((edition) => (
            <li
              key={edition.id}
              className="flex flex-wrap items-center gap-x-5 gap-y-2 py-3 text-xs"
            >
              <span className="min-w-36 font-mono">
                {formatUtc(edition.due_at_utc ?? edition.created_at)}
              </span>
              <span className="min-w-28 font-semibold">{statusLabel(edition)}</span>
              <span className="text-muted">
                {formatUtc(edition.requested.start)} to {formatUtc(edition.requested.end)}
              </span>
              {edition.safe_reason === 'capacity_wait' && (
                <span className="text-amber">Waiting for queue space</span>
              )}
              {edition.safe_reason === 'research_usage_limit' && (
                <span className="text-amber">
                  Research allowance reached for the subscription owner. This run will retry after
                  their allowance resets or an administrator increases their level.
                </span>
              )}
              <span className="ml-auto">{editionLink(edition)}</span>
              {edition.accepted_as_baseline && (
                <span className="text-good">Accepted for comparison</span>
              )}
              {edition.comparison && (
                <div className="basis-full border-l-2 border-ember/70 pl-3 text-xs">
                  <p className="font-semibold">
                    {edition.comparison.previous_version_id
                      ? 'Compared with the previous report'
                      : 'Comparison status'}
                  </p>
                  <p className="mt-1 text-muted">{edition.comparison.summary}</p>
                  {(edition.comparison.changed_claims > 0 ||
                    edition.comparison.corrected_evidence > 0 ||
                    edition.comparison.novel_evidence > 0) && (
                    <p className="mt-1 text-muted">
                      {edition.comparison.changed_claims} changed assessment
                      {edition.comparison.changed_claims === 1 ? '' : 's'} ·{' '}
                      {edition.comparison.corrected_evidence} source correction
                      {edition.comparison.corrected_evidence === 1 ? '' : 's'} ·{' '}
                      {edition.comparison.novel_evidence} new captured item
                      {edition.comparison.novel_evidence === 1 ? '' : 's'}
                    </p>
                  )}
                </div>
              )}
              {canManage && canAcceptBaseline(edition) && (
                <span className="basis-full">
                  {baselineConfirm === edition.id ? (
                    <span
                      role="group"
                      aria-label="Confirm comparison baseline"
                      className="space-y-2"
                    >
                      <span className="block text-muted">
                        Use this reviewed or partial report as context for future comparisons?
                        Missing coverage will stay marked as missing.
                      </span>
                      <span className="flex gap-2">
                        <Button
                          disabled={controlling !== null}
                          onClick={() => void acceptBaseline(edition)}
                        >
                          Confirm baseline
                        </Button>
                        <Button variant="secondary" onClick={() => setBaselineConfirm(null)}>
                          Cancel
                        </Button>
                      </span>
                    </span>
                  ) : (
                    <Button
                      variant="secondary"
                      disabled={controlling !== null}
                      onClick={() => setBaselineConfirm(edition.id)}
                    >
                      Use as comparison baseline
                    </Button>
                  )}
                </span>
              )}
              {canManage && edition.job_id && (
                <span className="flex gap-2">
                  {(['queued', 'running'].includes(edition.workflow) ||
                    edition.workflow === 'paused') && (
                    <Button
                      variant="secondary"
                      disabled={controlling !== null}
                      onClick={() =>
                        void control(edition, edition.workflow === 'paused' ? 'resume' : 'pause')
                      }
                    >
                      {edition.workflow === 'paused' ? 'Resume edition' : 'Pause edition'}
                    </Button>
                  )}
                  {['retry_wait', 'blocked'].includes(edition.workflow) && (
                    <Button
                      variant="secondary"
                      disabled={controlling !== null}
                      onClick={() => void control(edition, 'retry')}
                    >
                      Retry edition
                    </Button>
                  )}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
      {hasMore && (
        <Button
          variant="secondary"
          disabled={loading}
          onClick={() => void loadPage(items.length, false)}
        >
          Load older editions
        </Button>
      )}
    </section>
  );
}
