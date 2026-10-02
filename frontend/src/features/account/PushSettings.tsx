import { useEffect, useState } from 'react';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import { getPushSettings } from '@/lib/api/webPush';
import type { PushSettings as Settings } from '@/lib/api/webPush';
import { disablePush, enablePush, pushSupported } from '@/lib/browserPush';

export function PushSettings() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const supported = pushSupported();
  useEffect(() => {
    let active = true;
    void getPushSettings()
      .then((value) => {
        if (active) setSettings(value);
      })
      .catch(() => {
        if (active) setError('Browser push settings could not be loaded.');
      });
    return () => {
      active = false;
    };
  }, []);

  async function enable() {
    if (!settings?.public_key) return;
    // Start the permission request synchronously within this user gesture.
    const pending = enablePush(settings.public_key, settings.devices);
    setBusy(true);
    setError(null);
    try {
      await pending;
      setSettings(await getPushSettings());
    } catch {
      setError('Push could not be enabled. Check browser permission and try again.');
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    const device = settings?.devices.find((value) => value.id === id);
    if (!device) return;
    setBusy(true);
    setError(null);
    try {
      await disablePush(device);
      setSettings(await getPushSettings());
    } catch {
      setError('This device could not be removed. Try again.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="push-title" className="space-y-4 border-b border-line pb-8">
      <h2 id="push-title" className="text-xl font-semibold">
        Browser push
      </h2>
      <p className="text-sm text-muted">
        Opt in separately on each browser. Push goes through your browser provider and shows a
        generic notification on the lock screen. Alert titles, summaries and locations stay in the
        authenticated app. Signing out removes this session's registered devices.
      </p>
      <p className="text-sm text-muted">
        On iPhone and iPad, add this app to the Home Screen and open it there before enabling push.
      </p>
      {!supported && (
        <Alert tone="warning">
          This browser does not currently support push here. Use a supported browser over HTTPS, or
          an installed Home Screen app on iOS 16.4 or later.
        </Alert>
      )}
      {error && <Alert tone="error">{error}</Alert>}
      {!settings && !error && <LoadingNote label="Loading browser push settings…" />}
      {settings && (
        <>
          {!settings.available && (
            <Alert tone="warning">
              Browser push has not been configured for this installation.
            </Alert>
          )}
          <Button
            disabled={!supported || !settings.available || busy}
            onClick={() => void enable()}
          >
            {busy ? 'Updating…' : 'Enable push on this browser'}
          </Button>
          {settings.devices.length === 0 ? (
            <p className="text-sm text-muted">No browsers are subscribed.</p>
          ) : (
            <ul aria-label="Subscribed browsers" className="space-y-2">
              {settings.devices.map((device, index) => (
                <li key={device.id} className="flex items-center justify-between gap-3 text-sm">
                  <span>
                    Browser {index + 1}, registered{' '}
                    {new Date(device.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => void remove(device.id)}
                  >
                    Remove browser {index + 1}
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}
