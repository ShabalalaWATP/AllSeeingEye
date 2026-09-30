import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router';

import { Alert, LoadingNote } from '@/components/ui/Alert';
import { Button } from '@/components/ui/Button';
import {
  getEmailPreferences,
  getSubscriptionEmail,
  saveEmailPreferences,
  saveSubscriptionEmail,
} from '@/lib/api/notificationEmail';
import type { EmailPreferences, SubscriptionEmail } from '@/lib/api/notificationEmail';

export function EmailNotificationSettings() {
  const [params] = useSearchParams();
  const subscription = params.get('subscription');
  const [email, setEmail] = useState<EmailPreferences | null>(null);
  const [policy, setPolicy] = useState<SubscriptionEmail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    let current = true;
    void Promise.all([
      getEmailPreferences(),
      subscription ? getSubscriptionEmail(subscription) : Promise.resolve(null),
    ])
      .then(([preferences, rule]) => {
        if (current) {
          setEmail(preferences);
          setPolicy(rule);
        }
      })
      .catch(() => {
        if (current)
          setError('Email preferences could not be loaded. Your access may have changed.');
      });
    return () => {
      current = false;
    };
  }, [subscription]);

  async function save() {
    if (!email) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await saveEmailPreferences({ enabled: email.enabled, include_names: email.include_names });
      if (subscription && policy) await saveSubscriptionEmail(subscription, policy);
      setSaved(true);
    } catch {
      setError(
        'Email preferences could not be saved. Check email verification and current access.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      aria-labelledby="notification-email-title"
      className="space-y-4 border-b border-line pb-8"
    >
      <h2 id="notification-email-title" className="text-xl font-semibold">
        Subscription emails
      </h2>
      <p className="text-sm text-muted">
        Emails contain a secure link, with no report text, evidence or source titles. Choose email
        delivery separately for each subscription. You can disable all emails here.
      </p>
      {error && <Alert tone="error">{error}</Alert>}
      {!email && !error && <LoadingNote label="Loading email preferences…" />}
      {email && (
        <>
          <p className="text-sm">Destination: {email.destination}</p>
          {!email.available && (
            <Alert tone="warning">
              Email is not configured for this installation. Your subscription will continue to run.
              Delivery will remain unavailable until configured.
            </Alert>
          )}
          {!email.confirmed && (
            <p className="text-sm text-muted">
              Confirm ownership of this address by enrolling email verification in{' '}
              <Link className="underline" to="/account?section=security">
                Security
              </Link>{' '}
              before enabling email.
            </p>
          )}
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={email.enabled}
              disabled={busy || (!email.confirmed && !email.enabled)}
              onChange={(event) => {
                setSaved(false);
                setEmail({ ...email, enabled: event.target.checked });
              }}
            />
            Allow subscription emails to my account address
          </label>
          <label className="flex items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={email.include_names}
              disabled={busy}
              onChange={(event) => {
                setSaved(false);
                setEmail({ ...email, include_names: event.target.checked });
              }}
            />
            Include subscription names (may reveal sensitive topics)
          </label>
          {policy && (
            <fieldset className="space-y-3 border border-line p-4" disabled={busy}>
              <legend className="px-2 text-sm">This subscription</legend>
              <label className="block text-sm">
                Edition emails
                <select
                  className="mt-1 block rounded border border-line bg-surface-2 p-2"
                  value={policy.policy}
                  onChange={(event) => {
                    setSaved(false);
                    setPolicy({
                      ...policy,
                      policy: event.target.value as SubscriptionEmail['policy'],
                    });
                  }}
                >
                  <option value="none">None</option>
                  <option value="material_changes">Material changes</option>
                  <option value="every_edition">Every edition</option>
                </select>
              </label>
              <label className="flex items-start gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={policy.attention}
                  onChange={(event) => {
                    setSaved(false);
                    setPolicy({ ...policy, attention: event.target.checked });
                  }}
                />{' '}
                Notify me when this subscription needs attention
              </label>
            </fieldset>
          )}
          {!policy && (
            <p className="text-sm text-muted">
              Open Email preferences beside a subscription to choose its delivery policy.
            </p>
          )}
          <Button disabled={busy} onClick={() => void save()}>
            Save email preferences
          </Button>
          {saved && (
            <p role="status" className="text-sm">
              Email preferences saved. Pending sends use these settings.
            </p>
          )}
          <p className="text-xs text-muted">
            A relay timeout can leave acceptance uncertain. Such messages are not automatically
            resent. Email does not guarantee exactly-once delivery.
          </p>
        </>
      )}
    </section>
  );
}
