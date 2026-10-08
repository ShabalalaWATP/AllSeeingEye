import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { ConfirmButton } from '@/components/ui/ConfirmButton';
import { enableFeed, getFeedStatus, revokeFeed } from '@/lib/api/notifications';
import type { FeedStatus, FeedToken } from '@/lib/api/notifications';

export function PrivateFeedSettings() {
  const [status, setStatus] = useState<FeedStatus | null>(null);
  const [token, setToken] = useState<FeedToken | null>(null);
  const [titles, setTitles] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void getFeedStatus(controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setStatus(result);
          setTitles(result.include_titles);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setError('Feed settings could not be loaded.');
      });
    return () => controller.abort();
  }, []);

  async function change(enabled: boolean) {
    setPending(true);
    setError(null);
    setToken(null);
    try {
      if (enabled) setToken(await enableFeed(titles));
      else await revokeFeed();
      setStatus(await getFeedStatus());
    } catch {
      setError('Feed settings could not be saved. Reload the page and try again.');
    } finally {
      setPending(false);
    }
  }

  return (
    <section aria-labelledby="private-feed-title" className="space-y-4">
      <h2 id="private-feed-title" className="text-xl font-semibold">
        Private Atom feed
      </h2>
      <p className="text-sm text-muted">
        Follow your alerts and subscription editions in a feed reader. The feed contains links and
        generic labels, with no report text or evidence. Your reader can retain what it receives.
      </p>
      <p className="text-sm text-muted">
        This separate credential bypasses interactive sign-in for this feed only. Keep it private. A
        password or account security change invalidates it; signing out does not.
      </p>
      {error && <Alert tone="error">{error}</Alert>}
      {!status && !error && <LoadingNote label="Loading feed settings…" />}
      {status && (
        <>
          <p className="text-sm" role="status">
            {status.enabled ? 'Feed enabled' : 'Feed disabled'}
          </p>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={titles}
              disabled={pending}
              onChange={(event) => setTitles(event.target.checked)}
            />
            {status.enabled
              ? 'Include alert and subscription titles when the token is replaced (may reveal sensitive topics)'
              : 'Include alert and subscription titles (may reveal sensitive topics)'}
          </label>
          <div className="flex flex-wrap gap-3">
            {status.enabled ? (
              <>
                <ConfirmButton
                  label="Replace feed token"
                  variant="primary"
                  tone="primary"
                  busy={pending}
                  title="Replace the private feed token?"
                  confirmLabel="Replace token"
                  busyLabel="Replacing token…"
                  onConfirm={() => void change(true)}
                >
                  <p>
                    A new token is created and shown once. The old token stops working immediately,
                    so update every feed reader that uses it.
                  </p>
                  <p>
                    Titles will {titles ? '' : 'not '}be included in the feed for the new token.
                  </p>
                </ConfirmButton>
                <ConfirmButton
                  label="Revoke feed token"
                  busy={pending}
                  title="Revoke the private feed token?"
                  confirmLabel="Revoke token"
                  busyLabel="Revoking token…"
                  onConfirm={() => void change(false)}
                >
                  <p>
                    The feed is disabled and the current token stops working immediately. Feed
                    readers that use it receive nothing further.
                  </p>
                  <p>You can enable the feed again later; it gets a new token.</p>
                </ConfirmButton>
              </>
            ) : (
              <Button disabled={pending} onClick={() => void change(true)}>
                Enable feed
              </Button>
            )}
          </div>
        </>
      )}
      {token && (
        <div className="space-y-3 rounded border border-line p-4">
          <p className="text-sm">
            Shown once. Configure HTTP Basic authentication in your feed reader. Use HTTPS outside
            local development. Replacing the token ends access for the old one.
          </p>
          <label className="block text-sm">
            Feed URL
            <input
              className="mt-1 block w-full rounded border border-control-border bg-surface-2 p-2"
              value={token.feed_url}
              readOnly
            />
          </label>
          <label className="block text-sm">
            Username
            <input
              className="mt-1 block w-full rounded border border-control-border bg-surface-2 p-2"
              value={token.username}
              readOnly
            />
          </label>
          <label className="block text-sm">
            Feed password
            <input
              className="mt-1 block w-full rounded border border-control-border bg-surface-2 p-2"
              value={token.token}
              readOnly
              autoComplete="off"
            />
          </label>
          <Button onClick={() => setToken(null)}>Hide token</Button>
        </div>
      )}
    </section>
  );
}
