import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { getDigestPreferences, saveDigestPreferences } from '@/lib/api/notificationDigest';
import type { DigestPreferences } from '@/lib/api/notificationDigest';

export function DigestSettings() {
  const [preferences, setPreferences] = useState<DigestPreferences | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    let active = true;
    void getDigestPreferences()
      .then((value) => {
        if (active) setPreferences(value);
      })
      .catch(() => {
        if (active) setError('Daily digest settings could not be loaded.');
      });
    return () => {
      active = false;
    };
  }, []);

  async function save() {
    if (!preferences) return;
    setBusy(true);
    setSaved(false);
    setError(null);
    try {
      await saveDigestPreferences(preferences);
      setSaved(true);
    } catch {
      setError('Check the time zone and enable account email with a verified address first.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="digest-title" className="space-y-4 border-b border-line pb-8">
      <h2 id="digest-title" className="text-xl font-semibold">
        Daily digest
      </h2>
      <p className="text-sm text-muted">
        One email per local day with counts and secure links for alerts, completed or failed
        research, and forecast review dates. Empty periods send no email. Titles and report text are
        never included. Account email must be enabled above.
      </p>
      {error && <Alert tone="error">{error}</Alert>}
      {!preferences && !error && <LoadingNote label="Loading daily digest settings…" />}
      {preferences && (
        <>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={preferences.enabled}
              disabled={busy}
              onChange={(event) =>
                setPreferences({ ...preferences, enabled: event.target.checked })
              }
            />
            Send a daily digest
          </label>
          <label className="block text-sm">
            Time zone (for example Europe/London)
            <input
              value={preferences.timezone}
              disabled={busy}
              maxLength={100}
              className="mt-1 block rounded border border-control-border bg-surface px-3 py-2"
              onChange={(event) => setPreferences({ ...preferences, timezone: event.target.value })}
            />
          </label>
          <label className="block text-sm">
            Local hour (0 to 23)
            <input
              type="number"
              min={0}
              max={23}
              value={preferences.hour}
              disabled={busy}
              className="mt-1 block rounded border border-control-border bg-surface px-3 py-2"
              onChange={(event) =>
                setPreferences({ ...preferences, hour: Number(event.target.value) })
              }
            />
          </label>
          <p className="text-sm text-muted">
            A clock change uses the first occurrence of a repeated hour, or the first valid time
            after a missing hour. An outage combines missed activity into the next digest. Counts
            cover retained records since the previous scheduled window, or your opt-in.
          </p>
          <Button onClick={() => void save()} disabled={busy}>
            {busy ? 'Saving…' : 'Save digest settings'}
          </Button>
          {saved && (
            <p role="status" className="text-sm">
              Daily digest settings saved.
            </p>
          )}
        </>
      )}
    </section>
  );
}
