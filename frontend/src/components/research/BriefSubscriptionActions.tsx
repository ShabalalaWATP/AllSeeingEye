import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router';

import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { ApiError, describeError } from '@/lib/api/errors';
import {
  createBriefSubscription,
  type BriefSubscriptionSettings,
} from '@/lib/api/briefSubscriptions';
import type { BriefDraft, ResearchBrief } from '@/lib/api/researchBriefSchema';
import { briefCanSubscribe } from '@/lib/researchBriefDraft';

import { BriefSubscriptionForm } from './BriefSubscriptionForm';

export function BriefSubscriptionActions({
  brief,
  draft,
  dirty,
  editorBusy,
  initialOpen,
}: {
  brief: ResearchBrief | null;
  draft: BriefDraft;
  dirty: boolean;
  editorBusy: boolean;
  initialOpen: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<string | null>(null);
  const [verificationFailed, setVerificationFailed] = useState(false);
  const request = useRef<AbortController | null>(null);
  useEffect(() => () => request.current?.abort(), []);
  const reason = briefCanSubscribe(draft);
  const create = async (settings: BriefSubscriptionSettings) => {
    if (!brief || dirty || busy || editorBusy || reason || verificationFailed) return;
    setBusy(true);
    setError(null);
    const controller = new AbortController();
    request.current = controller;
    try {
      const schedule = await createBriefSubscription(brief, settings, controller.signal);
      if (
        schedule.brief_id !== brief.identity.id ||
        schedule.brief_revision !== brief.identity.revision
      ) {
        setVerificationFailed(true);
        throw new ApiError(
          502,
          'invalid_response',
          'The saved subscription referenced a different brief revision.',
        );
      }
      setCreated(schedule.id);
      setOpen(false);
    } catch (caught) {
      setError(describeError(caught));
    } finally {
      setBusy(false);
      request.current = null;
    }
  };
  return (
    <div className="space-y-3">
      <Button
        variant="secondary"
        disabled={!brief || dirty || !!reason || editorBusy || busy || verificationFailed}
        aria-describedby={reason ? 'brief-subscribe-unavailable' : undefined}
        onClick={() => setOpen(true)}
      >
        Subscribe to updates
      </Button>
      {reason && (
        <p id="brief-subscribe-unavailable" className="text-xs text-muted">
          Subscription unavailable: {reason}
        </p>
      )}
      {verificationFailed && error && (
        <Alert tone="error">
          {error}{' '}
          <Link to="/subscriptions" className="underline">
            Review subscriptions
          </Link>
        </Alert>
      )}
      {created && (
        <p role="status" className="text-sm text-ember">
          Subscription created from brief revision {brief?.identity.revision}.{' '}
          <Link className="underline" to="/subscriptions">
            View subscriptions
          </Link>
        </p>
      )}
      {open && brief && !dirty && !reason && !verificationFailed && (
        <BriefSubscriptionForm
          key={`${brief.identity.id}:${brief.identity.revision}`}
          brief={brief}
          busy={busy}
          error={error}
          onCreate={(settings) => void create(settings)}
          onCancel={() => {
            setOpen(false);
            setError(null);
          }}
        />
      )}
    </div>
  );
}
