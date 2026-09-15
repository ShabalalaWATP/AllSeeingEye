import { useEffect, useRef, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { describeError } from '@/lib/api/errors';
import { fetchSubscriptionEvents, type SubscriptionEvent } from '@/lib/api/subscriptionControls';
import { formatUtc } from '@/lib/format';

function eventLabel(event: SubscriptionEvent): string {
  if (event.event_kind === 'material_change') return 'Material change identified';
  return 'Subscription update';
}

export function SubscriptionActivity({ subscriptionId }: { subscriptionId: string }) {
  const [shown, setShown] = useState(false);
  const [items, setItems] = useState<SubscriptionEvent[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pending = useRef<AbortController | null>(null);

  useEffect(() => () => pending.current?.abort(), []);

  const load = async () => {
    pending.current?.abort();
    const controller = new AbortController();
    pending.current = controller;
    setLoading(true);
    setError(null);
    try {
      const page = await fetchSubscriptionEvents(subscriptionId, controller.signal);
      if (!controller.signal.aborted) setItems(page.items);
    } catch (cause) {
      if (!controller.signal.aborted) setError(describeError(cause));
    } finally {
      if (pending.current === controller) {
        pending.current = null;
        setLoading(false);
      }
    }
  };

  return (
    <div className="mb-3 border-b border-line/60 pb-3">
      <Button
        variant="secondary"
        aria-expanded={shown}
        onClick={() => {
          setShown((value) => !value);
          if (shown) pending.current?.abort();
          if (!shown && items === null) void load();
        }}
      >
        Activity
      </Button>
      {shown && (
        <div className="mt-3 text-xs">
          {loading && <LoadingNote label="Loading subscription activity" />}
          {error && (
            <Alert tone="error">
              {error} <Button onClick={() => void load()}>Retry activity</Button>
            </Alert>
          )}
          {items?.length === 0 && !error && <p className="text-muted">No change alerts yet.</p>}
          {items && items.length > 0 && (
            <ul className="space-y-2" aria-label="Subscription activity">
              {items.map((event) => (
                <li key={event.id} className="flex flex-wrap gap-x-3">
                  <span className="font-medium">{eventLabel(event)}</span>
                  <span className="text-muted">{formatUtc(event.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
