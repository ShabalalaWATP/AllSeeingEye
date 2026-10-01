import { useCallback, useState } from 'react';

import { Button } from '@/components/ui/Button';
import { setMutedKinds, unmuteRule } from '@/lib/api/bell';
import type { BellKind } from '@/lib/api/bell';
import { describeError } from '@/lib/api/errors';

import { headingClass } from './BellAlertList';
import type { NotificationBellState } from './useNotificationBell';

export const BELL_KINDS: readonly { kind: BellKind; label: string; detail: string }[] = [
  { kind: 'alerts', label: 'Alerts', detail: 'Unacknowledged alerts from your rules and teams.' },
  { kind: 'research', label: 'Finished research', detail: 'Research runs that have finished.' },
];

/**
 * The account's in-app bell choices. They change only what this account sees in the bell
 * and its badge: rules keep running, nothing is acknowledged and other people are unaffected.
 */
export function BellSettings({ state }: { state: NotificationBellState }) {
  const { preferences, updateBell, refresh } = state;
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState('');

  const run = useCallback(
    async (key: string, work: () => Promise<void>, done: string) => {
      if (busy !== null) return;
      setBusy(key);
      setError(null);
      try {
        await work();
        setStatus(done);
        await refresh();
      } catch (caught) {
        setError(`${describeError(caught)} Your previous setting is unchanged. Try again.`);
      } finally {
        setBusy(null);
      }
    },
    [busy, refresh],
  );

  if (preferences === null)
    return <p className="px-2 text-sm text-muted">Settings are loading or unavailable.</p>;
  const muted = new Set(preferences.muted_kinds);
  const toggle = (kind: BellKind, label: string) => {
    const next = new Set(muted);
    if (next.has(kind)) next.delete(kind);
    else next.add(kind);
    void run(
      kind,
      async () => {
        const saved = await setMutedKinds([...next]);
        updateBell((bell) => ({ ...bell, preferences: saved }));
      },
      `${label} ${next.has(kind) ? 'hidden from' : 'shown in'} your bell.`,
    );
  };

  return (
    <section aria-labelledby="bell-settings-heading" className="space-y-3">
      <h3 id="bell-settings-heading" className={headingClass}>
        Notification settings
      </h3>
      <p className="px-2 text-xs text-muted">
        These choices are saved to your account and change only your bell and its count. Alert rules
        keep running, and their Enabled switch is on the Alerts page.
      </p>
      <fieldset className="space-y-1 px-2" disabled={busy !== null}>
        <legend className="text-sm text-text">Show in my bell</legend>
        {BELL_KINDS.map(({ kind, label, detail }) => (
          <label key={kind} className="flex min-h-11 items-start gap-2 py-1 text-sm">
            <input
              type="checkbox"
              className="mt-1 accent-ember"
              checked={!muted.has(kind)}
              aria-describedby={`bell-kind-${kind}`}
              onChange={() => toggle(kind, label)}
            />
            <span>
              {label}
              <span id={`bell-kind-${kind}`} className="block text-xs text-muted">
                {detail}
              </span>
            </span>
          </label>
        ))}
      </fieldset>
      <div className="px-2">
        <h4 className="text-sm text-text">Muted alert rules</h4>
        {preferences.muted_rules.length === 0 ? (
          <p className="text-xs text-muted">
            None. Use Mute rule on an alert to stop that rule adding to your bell.
          </p>
        ) : (
          <ul className="mt-1 space-y-1">
            {preferences.muted_rules.map((rule) => (
              <li key={rule.indicator_id} className="flex items-center justify-between gap-2">
                <span className="text-sm">{rule.name}</span>
                <Button
                  variant="ghost"
                  className="min-h-11 px-2 text-xs"
                  busy={busy === rule.indicator_id}
                  disabled={busy !== null && busy !== rule.indicator_id}
                  aria-label={`Unmute ${rule.name}`}
                  onClick={() =>
                    void run(
                      rule.indicator_id,
                      async () => {
                        const saved = await unmuteRule(rule.indicator_id);
                        updateBell((bell) => ({ ...bell, preferences: saved }));
                      },
                      `${rule.name} unmuted.`,
                    )
                  }
                >
                  Unmute
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p role="status" className="sr-only">
        {status}
      </p>
      {error && (
        <p role="alert" className="px-2 text-xs text-critical">
          {error}
        </p>
      )}
    </section>
  );
}
