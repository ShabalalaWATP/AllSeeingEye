import { useEffect, useRef, useState } from 'react';

import { BriefSubscriptionForm } from '@/components/research/BriefSubscriptionForm';
import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  createBriefSubscription,
  briefSubscriptionSettingsSchema,
} from '@/lib/api/briefSubscriptions';
import type { BriefSubscriptionSettings } from '@/lib/api/briefSubscriptions';
import { ApiError, describeError } from '@/lib/api/errors';
import { fetchBrief } from '@/lib/api/researchBriefs';
import type { ResearchBrief } from '@/lib/api/researchBriefSchema';
import type { Schedule } from '@/lib/api/schedules';

export function BriefScheduleCopy({
  source,
  onCancel,
  onCreated,
}: {
  source: Schedule;
  onCancel: () => void;
  onCreated: () => void;
}) {
  const [brief, setBrief] = useState<ResearchBrief | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [verificationFailed, setVerificationFailed] = useState(false);
  const [retry, setRetry] = useState(0);
  const request = useRef<AbortController | null>(null);
  const briefId = source.brief_id;
  const revision = source.brief_revision;
  const missingReference = !briefId || !revision;
  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (!briefId || !revision) return;
    const controller = new AbortController();
    request.current = controller;
    void fetchBrief(briefId, revision, controller.signal)
      .then((value) => setBrief(value))
      .catch((caught: unknown) => {
        if (!controller.signal.aborted) setError(describeError(caught));
      });
    return () => controller.abort();
  }, [briefId, revision, retry]);

  const parsed = briefSubscriptionSettingsSchema.safeParse({
    name: `Copy of ${source.name}`.slice(0, 120),
    timezone: source.timezone ?? 'UTC',
    local_hour: source.local_hour ?? source.hour_utc,
    local_minute: source.local_minute ?? 0,
    cadence: source.cadence,
    weekday: source.weekday,
    monthday: source.monthday,
    anchor_month: source.anchor_month,
    collection_policy: source.collection_policy ?? 'rolling_snapshot',
    enabled: false,
    notify_on_change: source.notify_on_change,
    avoid_repetition: source.avoid_repetition,
  });
  const create = async (settings: BriefSubscriptionSettings) => {
    if (!brief || !briefId || !revision || busy || verificationFailed) return;
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    request.current = controller;
    try {
      const created = await createBriefSubscription(
        brief,
        { ...settings, enabled: false },
        controller.signal,
      );
      if (created.brief_id !== briefId || created.brief_revision !== revision || created.enabled) {
        setVerificationFailed(true);
        throw new ApiError(
          502,
          'invalid_response',
          'The copy did not retain the exact brief revision and paused state. Review subscriptions before trying again.',
        );
      }
      onCreated();
    } catch (caught) {
      if (!controller.signal.aborted) setError(describeError(caught));
    } finally {
      setBusy(false);
      request.current = null;
    }
  };

  return (
    <section aria-label={`Copy ${source.name}`} className="max-w-2xl space-y-3">
      {missingReference && (
        <Alert tone="error">
          The linked Research Brief revision is missing. This subscription cannot be copied.{' '}
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </Alert>
      )}
      {!missingReference && !brief && !error && (
        <LoadingNote label="Loading the exact Research Brief revision" />
      )}
      {!brief && error && (
        <Alert tone="error">
          {error}{' '}
          <Button
            variant="secondary"
            onClick={() => {
              setBrief(null);
              setError(null);
              setRetry((value) => value + 1);
            }}
          >
            Retry brief
          </Button>
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </Alert>
      )}
      {brief && !parsed.success && (
        <Alert tone="error">
          This subscription has invalid recurrence settings and cannot be copied.{' '}
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
        </Alert>
      )}
      {brief && parsed.success && (
        <BriefSubscriptionForm
          brief={brief}
          initialSettings={parsed.data}
          duplicate
          busy={busy || verificationFailed}
          error={error}
          onCreate={(settings) => void create(settings)}
          onCancel={onCancel}
        />
      )}
    </section>
  );
}
